# -*- coding: utf-8 -*-
# Copyright 2017-2019 The pyXem developers
#
# This file is part of pyXem.
#
# pyXem is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyXem is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyXem.  If not, see <http://www.gnu.org/licenses/>.
import numpy as np

from scipy.ndimage import distance_transform_edt, label

from skimage.feature import peak_local_max, match_template
from skimage.filters import sobel
from skimage.morphology import watershed

from hyperspy.signals import Signal2D
from hyperspy.drawing.utils import plot_images


def normalize_vdf(im):
    """Normalizes image intensity by dividing by maximum value.

    Parameters
    ----------
    im : np.array()
        Array of image intensities

    Returns
    -------
    imn : np.array()
        Array of normalized image intensities

    """
    imn = im / im.max()
    return imn


def norm_cross_corr(image, template):
    """Calculates the normalised cross-correlation between an image
    and a template using match_template from skimage.feature.

    Parameters
    ----------
    image: np.array
        Image
    template: np.array
        Reference image
        
    Returns
    -------
    corr : float
        Normalised cross-correlation between image and template at zero
        displacement.
    """
    # If image and template are alike, 1 will be returned.
    if np.array_equal(image,template):
        corr = 1.
    else: 
        # Return only the value in the middle, i.e. at zero displcement
        corr = match_template(image=image, template=template, pad_input=True,
                              mode='constant', constant_values=0) \
            [int(np.shape(image)[0]/2), int(np.shape(image)[1]/2)]
    return corr


def get_vector_i(gvectors_of_add_indices, add_indices, gvector_i):
    """Obtain an array of shape (n, 2) containing the vectors found in
    gvectors_of_add_indices, which itself may contain objects with
    different shapes.

    Parameters
    ----------
    gvectors_of_add_indices : np.array of object
        All vectors that should be found in the returned g. Should be
        equal to gvector_i[add_indices].
    add_indices : np.array of int
        Indices for the vectors from gvector_i found in
        gvectors_of_add_indices.
    gvector_i : ndarray
        Array of gvectors.
        
    Returns
    -------
    g : np.array of object
        Vectors in the form of an object of shape (n, 2) with all the
        n vectors found in gvectors_of_add_indices.
    """
    if len(np.shape(gvector_i)) == 1:
        g = np.array([gvector_i])
    else:
        g = gvector_i

    for i in range(np.shape(add_indices)[0]):

        if len(np.shape(gvectors_of_add_indices[i])) == 1:
            g = np.append(g, np.array([gvectors_of_add_indices[i]]), axis=0)
            
        elif len(np.shape(gvectors_of_add_indices[i])) == 2:
            g = np.append(g, gvectors_of_add_indices[i], axis=0)

    # Delete vectors that are equal:
    g_delete = []
    for i in range(np.shape(g)[0]):
        g_in_list = sum(map(lambda x: np.array_equal(g[i], x), g[i+1:]))

        if g_in_list:
            g_delete = np.append(g_delete, i)

    g = np.delete(g, g_delete, axis=0)

    return g


def separate(vdf_temp, min_distance, threshold, min_size, max_size,
             max_number_of_grains, exclude_border=False, plot_on=False):
    """Separate segments from one VDF image using edge-detection by the
    sobel transform and the watershed segmentation implemented in
    scikit-image. See [1,2] for examples from scikit-image.

    Parameters
    ----------
    vdf_temp : np.array
        One VDF image.
    min_distance: int
        Minimum distance (in pixels) between grains required for them to
        be considered as separate grains.
    threshold : float
        Threshold value between 0-1 for the VDF image. Pixels with
        values below (threshold*max intensity in VDF) are discarded.
    min_size : float
        Grains with size (i.e. total number of pixels) below min_size
        are discarded.
    max_size : float
        Grains with size (i.e. total number of pixels) above max_size
        are discarded.
    max_number_of_grains : int
        Maximum number of grains included in the returned separated
        grains. If it is exceeded, those with highest peak intensities
        will be returned.
    exclude_border : int or True, optional
        If non-zero integer, peaks within a distance of exclude_border
        from the boarder will be discarded. If True, peaks at or closer
        than min_distance of the boarder, will be discarded.
    plot_on : bool
        If True, the VDF, the thresholded VDF, the distance transform
        and the separated grains will be plotted in one figure window.

    Returns
    -------
    sep : np.array
        Array containing segments from VDF images (i.e. separated
        grains). Shape: (image size x, image size y, number of grains)

    References
    ----------
    [1] http://scikit-image.org/docs/dev/auto_examples/segmentation/
        plot_watershed.html
    [2] http://scikit-image.org/docs/dev/auto_examples/xx_applications/
        plot_coins_segmentation.html#sphx-glr-auto-examples-xx-
        applications-plot-coins-segmentation-py
    """

    # Create a mask by thresholding the input VDF
    mask = vdf_temp > (threshold * np.max(vdf_temp))

    # Calculate the eucledian distance from each point in a binary image to the
    # background point of value 0, that has the smallest distance to all input
    # points.
    distance = distance_transform_edt(mask)

    # Find the coordinates of the local maxima of the distance transform that
    # lie inside a region defined by (2*min_distance+1).
    local_maxi = peak_local_max(distance, indices=False,
                                min_distance=min_distance,
                                num_peaks=max_number_of_grains,
                                exclude_border=exclude_border, labels=mask)

    # Find the edges using the sobel transform.
    elevation = sobel(vdf_temp)

    # 'Flood' the elevation (i.e. edge) image from basins at the marker
    # positions. The marker positions are the local maxima of the
    # distance. Find the locations where different basins meet, i.e. the
    # watershed lines (segment boundaries). Only search for segments
    # (labels) in the area defined by mask (thresholded input VDF).
    labels = watershed(elevation, markers=label(local_maxi)[0], mask=mask)

    if not np.max(labels):
        print('No labels were found. Check input parameters.')

    sep = np.zeros((np.shape(vdf_temp)[0], np.shape(vdf_temp)[1],
                    (np.max(labels))), dtype='int32')
    n, i = 1, 0
    while (np.max(labels)) > n - 1:
        sep_temp = labels * (labels == n) / n
        sep_temp = np.nan_to_num(sep_temp)
        # Discard segment if it is too small, or add it to separated segments.
        if ((np.sum(sep_temp, axis=(0, 1)) < min_size)
                or (max_size is not None
                    and np.sum(sep_temp, axis=(0, 1)) > max_size)):
            sep = np.delete(sep, ((n - i) - 1), axis=2)
            i = i + 1
        else:
            sep[:, :, (n - i) - 1] = sep_temp
        n = n + 1
    # Put the intensity from the input VDF image into each segment area.
    vdf_sep = np.broadcast_to(vdf_temp.T, np.shape(sep.T)) * (sep.T == 1)

    if plot_on:
        # If segments have been discarded, make new labels that do not
        # include the discarded segments.
        if np.max(labels) != (np.shape(sep)[2]) and (np.shape(sep)[2] != 0):
            print('in if')
            labels = sep[:, :, 0]
            for i in range(1, np.shape(sep)[2]):
                labels = labels + sep[..., i] * (i + 1)
        # If no separated particles were found, set all elements in labels to 0.
        elif np.shape(sep)[2] == 0:
            labels = np.zeros(np.shape(labels))
            print('No separate particles were found.')
        plot_images([Signal2D(vdf_temp), Signal2D(mask), Signal2D(distance),
                     Signal2D(labels), Signal2D(elevation),
                     Signal2D(np.sum(vdf_sep, axis=0).T)],
                    axes_decor='off', per_row=3, colorbar=True, cmap='gnuplot2',
                    label=['VDF', 'Mask', 'Distances', 'Labels', 'Elevation',
                           'Separated particles'])
    return vdf_sep
