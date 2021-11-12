# Authors: Arash Dehghan Banadaki <adehgha@ncsu.edu>, Srikanth Patala <spatala@ncsu.edu>
# Copyright (c) 2015,  Arash Dehghan Banadaki and Srikanth Patala.
# License: GNU-GPL Style.
# How to cite GBpy:
# Banadaki, A. D. & Patala, S. "An efficient algorithm for computing the primitive bases of a general lattice plane",
# Journal of Applied Crystallography 48, 585-588 (2015). doi:10.1107/S1600576715004446


import numpy as np
import os, sys, inspect
import integer_manipulations as int_man
# -----------------------------------------------------------------------------------------------------------



def vrrotvec2mat(ax_ang):
    """
    Create a Rotation Matrix from Axis-Angle vector:

    Parameters
    ----------
    ``ax_ang``: numpy 5xn array
        The 3D rotation axis and angle (ax_ang) \v
        5 entries: \v
        First 3: axis \v
        4: angle \v
        5: 1 for proper and -1 for improper \v

    Returns
    -------
    mtx: nx3x3 numpy array
        3x3 rotation matrices

    See Also
    --------
    mat2quat, axang2quat, vrrotmat2vec
    """
    
    #file_dir = os.path.dirname(os.path.realpath(__file__))
    #path_dir2 = file_dir + '/../geometry/'
    #sys.path.append(path_dir2)
    
    if ax_ang.ndim == 1:
        if np.size(ax_ang) == 5:
            ax_ang = np.reshape(ax_ang, (5, 1))
            msz = 1
        elif np.size(ax_ang) == 4:
            ax_ang = np.reshape(np.hstack((ax_ang, np.array([1]))), (5, 1))
            msz = 1
        else:
            raise Exception('Wrong Input Type')
    elif ax_ang.ndim == 2:
        if np.shape(ax_ang)[0] == 5:
            msz = np.shape(ax_ang)[1]
        elif np.shape(ax_ang)[1] == 5:
            ax_ang = ax_ang.transpose()
            msz = np.shape(ax_ang)[1]
        else:
            raise Exception('Wrong Input Type')
    else:
        raise Exception('Wrong Input Type')

    direction = ax_ang[0:3, :]
    angle = ax_ang[3, :]

    d = np.array(direction, dtype=np.float64)
    d /= np.linalg.norm(d, axis=0)
    x = d[0, :]
    y = d[1, :]
    z = d[2, :]
    c = np.cos(angle)
    s = np.sin(angle)
    tc = 1 - c

    mt11 = tc*x*x + c
    mt12 = tc*x*y - s*z
    mt13 = tc*x*z + s*y

    mt21 = tc*x*y + s*z
    mt22 = tc*y*y + c
    mt23 = tc*y*z - s*x

    mt31 = tc*x*z - s*y
    mt32 = tc*y*z + s*x
    mt33 = tc*z*z + c

    mtx = np.column_stack((mt11, mt12, mt13, mt21, mt22, mt23, mt31, mt32, mt33))

    inds1 = np.where(ax_ang[4, :] == -1)
    mtx[inds1, :] = -mtx[inds1, :]

    if msz == 1:
        mtx = mtx.reshape(3, 3)
    else:
        mtx = mtx.reshape(msz, 3, 3)

    return mtx
# -----------------------------------------------------------------------------------------------------------


def vrrotmat2vec(mat1, rot_type='proper'):
    """
    Create an axis-angle np.array from Rotation Matrix:

    Parameters
    ----------
    mat1: nx3x3 numpy array
        The nx3x3 rotation matrices to convert
    rot_type: string ('proper' or 'improper')
        ``improper`` if there is a possibility of
        having improper matrices in the input,
        ``proper`` otherwise. \v
        Default: ``proper``

    Returns
    -------
    ``ax_ang``: numpy 5xn array
        The 3D rotation axis and angle (ax_ang) \v
        5 entries: \v
        First 3: axis \v
        4: angle \v
        5: 1 for proper and -1 for improper \v

    See Also
    --------
    mat2quat, axang2quat, vrrotvec2mat
    """
    mat = np.copy(mat1)
    if mat.ndim == 2:
        if np.shape(mat) == (3, 3):
            mat = np.copy(np.reshape(mat, (1, 3, 3)))
        else:
            raise Exception('Wrong Input Type')
    elif mat.ndim == 3:
        if np.shape(mat)[1:] != (3, 3):
            raise Exception('Wrong Input Type')
    else:
        raise Exception('Wrong Input Type')

    msz = np.shape(mat)[0]
    ax_ang = np.zeros((5, msz))

    epsilon = 1e-12
    if rot_type == 'proper':
        ax_ang[4, :] = np.ones(np.shape(ax_ang[4, :]))
    elif rot_type == 'improper':
        for i in range(msz):
            det1 = np.linalg.det(mat[i, :, :])
            if abs(det1 - 1) < epsilon:
                ax_ang[4, i] = 1
            elif abs(det1 + 1) < epsilon:
                ax_ang[4, i] = -1
                mat[i, :, :] = -mat[i, :, :]
            else:
                raise Exception('Matrix is not a rotation: |det| != 1')
    else:
        raise Exception('Wrong Input parameter for rot_type')



    mtrc = mat[:, 0, 0] + mat[:, 1, 1] + mat[:, 2, 2]


    ind1 = np.where(abs(mtrc - 3) <= epsilon)[0]
    ind1_sz = np.size(ind1)
    if np.size(ind1) > 0:
        ax_ang[:4, ind1] = np.tile(np.array([0, 1, 0, 0]), (ind1_sz, 1)).transpose()


    ind2 = np.where(abs(mtrc + 1) <= epsilon)[0]
    ind2_sz = np.size(ind2)
    if ind2_sz > 0:
        # phi = pi
        # This singularity requires elaborate sign ambiguity resolution

        # Compute axis of rotation, make sure all elements >= 0
        # real signs are obtained by flipping algorithm below
        diag_elems = np.concatenate((mat[ind2, 0, 0].reshape(ind2_sz, 1),
                                     mat[ind2, 1, 1].reshape(ind2_sz, 1),
                                     mat[ind2, 2, 2].reshape(ind2_sz, 1)), axis=1)
        axis = np.sqrt(np.maximum((diag_elems + 1)/2, np.zeros((ind2_sz, 3))))
        # axis elements that are <= epsilon are set to zero
        axis = axis*((axis > epsilon).astype(int))

        # Flipping
        #
        # The algorithm uses the elements above diagonal to determine the signs
        # of rotation axis coordinate in the singular case Phi = pi.
        # All valid combinations of 0, positive and negative values lead to
        # 3 different cases:
        # If (Sum(signs)) >= 0 ... leave all coordinates positive
        # If (Sum(signs)) == -1 and all values are non-zero
        #   ... flip the coordinate that is missing in the term that has + sign,
        #       e.g. if 2AyAz is positive, flip x
        # If (Sum(signs)) == -1 and 2 values are zero
        #   ... flip the coord next to the one with non-zero value
        #   ... ambiguous, we have chosen shift right

        # construct vector [M23 M13 M12] ~ [2AyAz 2AxAz 2AxAy]
        # (in the order to facilitate flipping):    ^
        #                                  [no_x  no_y  no_z ]

        m_upper = np.concatenate((mat[ind2, 1, 2].reshape(ind2_sz, 1),
                                  mat[ind2, 0, 2].reshape(ind2_sz, 1),
                                  mat[ind2, 0, 1].reshape(ind2_sz, 1)), axis=1)

        # elements with || smaller than epsilon are considered to be zero
        signs = np.sign(m_upper)*((abs(m_upper) > epsilon).astype(int))

        sum_signs = np.sum(signs, axis=1)
        t1 = np.zeros(ind2_sz,)
        tind1 = np.where(sum_signs >= 0)[0]
        t1[tind1] = np.ones(np.shape(tind1))

        tind2 = np.where(np.all(np.vstack(((np.any(signs == 0, axis=1) == False), t1 == 0)), axis=0))[0]
        t1[tind2] = 2*np.ones(np.shape(tind2))

        tind3 = np.where(t1 == 0)[0]
        flip = np.zeros((ind2_sz, 3))
        flip[tind1, :] = np.ones((np.shape(tind1)[0], 3))
        flip[tind2, :] = np.copy(-signs[tind2, :])

        t2 = np.copy(signs[tind3, :])

        shifted = np.column_stack((t2[:, 2], t2[:, 0], t2[:, 1]))
        flip[tind3, :] = np.copy(shifted + (shifted == 0).astype(int))

        axis = axis*flip
        ax_ang[:4, ind2] = np.vstack((axis.transpose(), np.pi*(np.ones((1, ind2_sz)))))

    ind3 = np.where(np.all(np.vstack((abs(mtrc + 1) > epsilon, abs(mtrc - 3) > epsilon)), axis=0))[0]
    ind3_sz = np.size(ind3)
    if ind3_sz > 0:
        phi = np.arccos((mtrc[ind3]-1)/2)
        den = 2*np.sin(phi)
        a1 = (mat[ind3, 2, 1]-mat[ind3, 1, 2])/den
        a2 = (mat[ind3, 0, 2]-mat[ind3, 2, 0])/den
        a3 = (mat[ind3, 1, 0]-mat[ind3, 0, 1])/den
        axis = np.column_stack((a1, a2, a3))
        ax_ang[:4, ind3] = np.vstack((axis.transpose(), phi.transpose()))

    return ax_ang
# -----------------------------------------------------------------------------------------------------------


def quat2mat(q):
    """
    Convert Quaternion Arrays to Rotation Matrix

        Parameters
    ----------
    q: numpy array (5 x 1)
        quaternion

    Returns
    ----------
    g: numpy array (3 x 3)
        rotation matrix

    See Also
    --------
    mat2quat, axang2quat
    """
    import quaternion as quat
    sz = quat.get_size(q)
    q0 = quat.getq0(q)
    q1 = quat.getq1(q)
    q2 = quat.getq2(q)
    q3 = quat.getq3(q)
    qt = quat.get_type(q)

    g = np.zeros((sz, 3, 3))
    g[:, 0, 0] = np.square(q0) + np.square(q1) - np.square(q2) - np.square(q3)
    g[:, 0, 1] = 2*(q1*q2 - q0*q3)
    g[:, 0, 2] = 2*(q3*q1 + q0*q2)
    g[:, 1, 0] = 2*(q1*q2 + q0*q3)
    g[:, 1, 1] = np.square(q0) - np.square(q1) + np.square(q2) - np.square(q3)
    g[:, 1, 2] = 2*(q2*q3 - q0*q1)
    g[:, 2, 0] = 2*(q3*q1 - q0*q2)
    g[:, 2, 1] = 2*(q2*q3 + q0*q1)
    g[:, 2, 2] = np.square(q0) - np.square(q1) - np.square(q2) + np.square(q3)

    if sz == 1:
        g = g.reshape((3, 3))
        if qt == -1:
            g = -g
    else:
        inds1 = np.where(qt == -1)
        g[inds1, :, :] = -g[inds1, :, :]

    return g
# -----------------------------------------------------------------------------------------------------------


def mat2quat(mat, rot_type='proper'):
    """
    Convert Rotation Matrices to Quaternions

    Parameters
    ----------
    mat: numpy array or a list of (3 x 3)
        rotation matrix

    rot_type: string ('proper' or 'improper')
        ``improper`` if there is a possibility of
        having improper matrices in the input,
        ``proper`` otherwise. \v
        Default: ``proper``

    Returns
    ----------
    quaternion_rep: numpy array (5 x 1)

    See Also
    --------
    quat2mat, axang2quat
    """
    import quaternion as quat
    ax_ang = vrrotmat2vec(mat, rot_type)
    q0 = np.cos(ax_ang[3, :]/2)
    q1 = ax_ang[0, :]*np.sin(ax_ang[3, :]/2)
    q2 = ax_ang[1, :]*np.sin(ax_ang[3, :]/2)
    q3 = ax_ang[2, :]*np.sin(ax_ang[3, :]/2)
    qtype = ax_ang[4, :]

    return quat.Quaternion(q0, q1, q2, q3, qtype)
# -----------------------------------------------------------------------------------------------------------



def unique_rows_tol(data, tol=1e-12, return_index=False, return_inverse=False):
    """
    This function returns the unique rows of the input matrix within that are within the
    specified tolerance.

    Parameters
    ----------
    data: numpy array (m x n)
    tol: double
        tolerance of comparison for each rows
        Default: 1e-12
    return_index: Boolean
        flag to return the index of unique rows based on the indices of the output
    return_inverse: Boolean
        flag to return the index of unique rows based on the indices of the input

    Returns
    ----------
    unique_rows: numpy array (m' x n)
    ia: numpy array, integer (m' x 1)
        unique rows based on the indices of the output
    ic: numpy array, integer (m x 1)
        unique rows based on the indices of the input

    See Also
    --------
    unique
    """
    prec = -np.fix(np.log10(tol))
    d_r = np.fix(data * 10 ** prec) / 10 ** prec + 0.0
    ### fix rounds off towards zero; issues with the case of 0.9999999998 and 1.0

    ### rint solves the issue, needs extensive testing
    # prec = -np.rint(np.log10(tol))
    # d_r = np.rint(data * 10 ** prec) / 10 ** prec + 0.0

    b = np.ascontiguousarray(d_r).view(np.dtype((np.void, d_r.dtype.itemsize * d_r.shape[1])))
    _, ia = np.unique(b, return_index=True)
    _, ic = np.unique(b, return_inverse=True)

    ret_arr = data[ia, :]
    if not return_index and not return_inverse:
        return ret_arr
    else:
        if return_index and return_inverse:
            return ret_arr, ia, ic
        elif return_index:
            return ret_arr, ia
        elif return_inverse:
            return ret_arr, ic

    # if not return_index and not return_inverse:
    #     return np.unique(b).view(d_r.dtype).reshape(-1, d_r.shape[1])
    # else:
    #     if return_index and return_inverse:
    #         return np.unique(b).view(d_r.dtype).reshape(-1, d_r.shape[1]), ia, ic
    #     elif return_index:
    #         return np.unique(b).view(d_r.dtype).reshape(-1, d_r.shape[1]), ia
    #     elif return_inverse:
    #         return np.unique(b).view(d_r.dtype).reshape(-1, d_r.shape[1]), ic
# -----------------------------------------------------------------------------------------------------------



