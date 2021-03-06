# -*- coding: utf-8 -*-
# Copyright 2017-2020 The pyXem developers
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

import pytest
import numpy as np
import dask.array as da
import hyperspy.api as hs

from pyxem.signals.diffraction2d import Diffraction2D, LazyDiffraction2D
from pyxem.signals.polar_diffraction2d import PolarDiffraction2D
from pyxem.detectors.generic_flat_detector import GenericFlatDetector
from pyxem.signals.diffraction1d import Diffraction1D


class TestComputeAndAsLazy2D:
    def test_2d_data_compute(self):
        dask_array = da.random.random((100, 150), chunks=(50, 50))
        s = LazyDiffraction2D(dask_array)
        scale0, scale1, metadata_string = 0.5, 1.5, "test"
        s.axes_manager[0].scale = scale0
        s.axes_manager[1].scale = scale1
        s.metadata.Test = metadata_string
        s.compute()
        assert isinstance(s, Diffraction2D)
        assert not hasattr(s.data, "compute")
        assert s.axes_manager[0].scale == scale0
        assert s.axes_manager[1].scale == scale1
        assert s.metadata.Test == metadata_string
        assert dask_array.shape == s.data.shape

    def test_4d_data_compute(self):
        dask_array = da.random.random((4, 4, 10, 15), chunks=(1, 1, 10, 15))
        s = LazyDiffraction2D(dask_array)
        s.compute()
        assert isinstance(s, Diffraction2D)
        assert dask_array.shape == s.data.shape

    def test_2d_data_as_lazy(self):
        data = np.random.random((100, 150))
        s = Diffraction2D(data)
        scale0, scale1, metadata_string = 0.5, 1.5, "test"
        s.axes_manager[0].scale = scale0
        s.axes_manager[1].scale = scale1
        s.metadata.Test = metadata_string
        s_lazy = s.as_lazy()
        assert isinstance(s_lazy, LazyDiffraction2D)
        assert hasattr(s_lazy.data, "compute")
        assert s_lazy.axes_manager[0].scale == scale0
        assert s_lazy.axes_manager[1].scale == scale1
        assert s_lazy.metadata.Test == metadata_string
        assert data.shape == s_lazy.data.shape

    def test_4d_data_as_lazy(self):
        data = np.random.random((4, 10, 15))
        s = Diffraction2D(data)
        s_lazy = s.as_lazy()
        assert isinstance(s_lazy, LazyDiffraction2D)
        assert data.shape == s_lazy.data.shape


class TestDecomposition:
    def test_decomposition_is_performed(self, diffraction_pattern):
        s = Diffraction2D(diffraction_pattern)
        s.decomposition()
        assert s.learning_results is not None

    def test_decomposition_class_assignment(self, diffraction_pattern):
        s = Diffraction2D(diffraction_pattern)
        s.decomposition()
        assert isinstance(s, Diffraction2D)


class TestAzimuthalIntegral:
    def test_azimuthal_integral_signal_type(self, dp_for_azimuthal):
        origin = [3.5, 3.5]
        detector = GenericFlatDetector(8, 8)
        dp_for_azimuthal.metadata.General.title = "A Title"
        dp_for_azimuthal.axes_manager[0].name = "x"
        ap = dp_for_azimuthal.get_azimuthal_integral(
            origin, detector=detector, detector_distance=1, wavelength=1, size_1d=5
        )

        assert isinstance(ap, Diffraction1D)
        assert dp_for_azimuthal.metadata.General.title == ap.metadata.General.title
        assert dp_for_azimuthal.axes_manager[0].name == ap.axes_manager[0].name

    @pytest.fixture
    def test_dp4D(self):
        dp = Diffraction2D(np.ones((5, 5, 5, 5)))
        return dp

    def test_azimuthal_integral_4D(self, test_dp4D):
        origin = [2, 2]
        detector = GenericFlatDetector(5, 5)
        ap = test_dp4D.get_azimuthal_integral(
            origin, detector=detector, detector_distance=1e6, wavelength=1, size_1d=4
        )
        assert isinstance(ap, Diffraction1D)
        assert np.array_equal(ap.data, np.ones((5, 5, 4)))

    @pytest.fixture
    def dp_for_axes_transfer(self):
        """Empty diffraction pattern for axes test.
        """
        dp = Diffraction2D(np.zeros((2, 2, 3, 3)))
        return dp

    def test_azimuthal_integral_axes(self, dp_for_axes_transfer):
        n_scale = 0.5
        dp_for_axes_transfer.axes_manager.navigation_axes[0].scale = n_scale
        dp_for_axes_transfer.axes_manager.navigation_axes[1].scale = 2 * n_scale
        name = "real_space"
        dp_for_axes_transfer.axes_manager.navigation_axes[0].name = name
        dp_for_axes_transfer.axes_manager.navigation_axes[1].units = name
        units = "um"
        dp_for_axes_transfer.axes_manager.navigation_axes[1].name = units
        dp_for_axes_transfer.axes_manager.navigation_axes[0].units = units

        origin = [1, 1]
        detector = GenericFlatDetector(3, 3)
        ap = dp_for_axes_transfer.get_azimuthal_integral(
            origin, detector=detector, detector_distance=1, wavelength=1, size_1d=5
        )
        rp_scale_x = ap.axes_manager.navigation_axes[0].scale
        rp_scale_y = ap.axes_manager.navigation_axes[1].scale
        rp_units_x = ap.axes_manager.navigation_axes[0].units
        rp_name_x = ap.axes_manager.navigation_axes[0].name
        rp_units_y = ap.axes_manager.navigation_axes[1].units
        rp_name_y = ap.axes_manager.navigation_axes[1].name

        assert n_scale == rp_scale_x
        assert 2 * n_scale == rp_scale_y
        assert units == rp_units_x
        assert name == rp_name_x
        assert name == rp_units_y
        assert units == rp_name_y

    @pytest.mark.parametrize(
        "expected",
        [
            (
                np.array(
                    [
                        [4.5, 3.73302794, 2.76374221, 1.87174165, 0.83391893, 0.0],
                        [0.75, 0.46369326, 0.24536559, 0.15187129, 0.06550021, 0.0],
                    ]
                )
            )
        ],
    )
    def test_azimuthal_integral_fast(self, dp_for_azimuthal, expected):
        origin = [3.5, 3.5]
        detector = GenericFlatDetector(8, 8)
        ap = dp_for_azimuthal.get_azimuthal_integral(
            origin, detector=detector, detector_distance=1e9, wavelength=1, size_1d=6
        )
        assert np.allclose(ap.data, expected, atol=1e-3)

    def test_azimuthal_integral_slow(self, dp_for_origin_variation):
        origin = np.array([[[0, 0], [1, 1]], [[1.5, 1.5], [2, 3]]])
        detector = GenericFlatDetector(4, 4)
        ap = dp_for_origin_variation.get_azimuthal_integral(
            origin, detector=detector, detector_distance=1e9, wavelength=1, size_1d=4
        )
        expected = np.array(
            [
                [
                    [1.01127149e-07, 4.08790171e-01, 2.93595970e-01, 0.00000000e00],
                    [2.80096084e-01, 4.43606853e-01, 1.14749573e-01, 0.00000000e00],
                ],
                [
                    [6.20952725e-01, 2.99225271e-01, 4.63002026e-02, 0.00000000e00],
                    [5.00000000e-01, 3.43071640e-01, 1.27089232e-01, 0.00000000e00],
                ],
            ]
        )
        assert np.allclose(ap.data, expected, atol=1e-5)


class TestPolarReprojection:
    def test_reproject_polar_signal_type(self, diffraction_pattern):
        polar = diffraction_pattern.as_polar()
        assert isinstance(polar, PolarDiffraction2D)

    def test_reproject_polar_axes(self, diffraction_pattern):
        n_scale = 0.5
        diffraction_pattern.axes_manager.navigation_axes[0].scale = n_scale
        diffraction_pattern.axes_manager.navigation_axes[1].scale = 2 * n_scale
        name = "real_space"
        diffraction_pattern.axes_manager.navigation_axes[0].name = name
        diffraction_pattern.axes_manager.navigation_axes[1].units = name
        units = "nm"
        diffraction_pattern.axes_manager.navigation_axes[1].name = units
        diffraction_pattern.axes_manager.navigation_axes[0].units = units

        polar = diffraction_pattern.as_polar()

        polar_scale_x = polar.axes_manager.navigation_axes[0].scale
        polar_scale_y = polar.axes_manager.navigation_axes[1].scale
        polar_units_x = polar.axes_manager.navigation_axes[0].units
        polar_name_x = polar.axes_manager.navigation_axes[0].name
        polar_units_y = polar.axes_manager.navigation_axes[1].units
        polar_name_y = polar.axes_manager.navigation_axes[1].name

        polar_t_axis = polar.axes_manager.signal_axes[0]
        polar_k_axis = polar.axes_manager.signal_axes[1]

        assert n_scale == polar_scale_x
        assert 2 * n_scale == polar_scale_y
        assert units == polar_units_x
        assert name == polar_name_x
        assert name == polar_units_y
        assert units == polar_name_y

        assert polar_t_axis.name == "theta"
        assert polar_t_axis.units == "$rad$"
        assert polar_k_axis.name == "k"
        assert polar_k_axis.units == "$rad$"


class TestVirtualImaging:
    # Tests that virtual imaging runs without failure

    @pytest.mark.parametrize("stack", [True, False])
    def test_plot_integrated_intensity(self, stack, diffraction_pattern):
        if stack:
            diffraction_pattern = hs.stack([diffraction_pattern] * 3)
        roi = hs.roi.CircleROI(3, 3, 5)
        diffraction_pattern.plot_integrated_intensity(roi)

    def test_get_integrated_intensity(self, diffraction_pattern):
        roi = hs.roi.CircleROI(3, 3, 5)
        vi = diffraction_pattern.get_integrated_intensity(roi)
        assert vi.data.shape == (2, 2)
        assert vi.axes_manager.signal_dimension == 2
        assert vi.axes_manager.navigation_dimension == 0

    @pytest.mark.parametrize("out_signal_axes", [None, (0, 1), (1, 2), ("x", "y")])
    def test_get_integrated_intensity_stack(self, diffraction_pattern, out_signal_axes):
        s = hs.stack([diffraction_pattern] * 3)
        s.axes_manager.navigation_axes[0].name = "x"
        s.axes_manager.navigation_axes[1].name = "y"

        roi = hs.roi.CircleROI(3, 3, 5)
        vi = s.get_integrated_intensity(roi, out_signal_axes)
        assert vi.axes_manager.signal_dimension == 2
        assert vi.axes_manager.navigation_dimension == 1
        if out_signal_axes == (1, 2):
            assert vi.data.shape == (2, 3, 2)
            assert vi.axes_manager.navigation_size == 2
            assert vi.axes_manager.signal_shape == (2, 3)
        else:
            assert vi.data.shape == (3, 2, 2)
            assert vi.axes_manager.navigation_size == 3
            assert vi.axes_manager.signal_shape == (2, 2)

    def test_get_integrated_intensity_out_signal_axes(self, diffraction_pattern):
        s = hs.stack([diffraction_pattern] * 3)
        roi = hs.roi.CircleROI(3, 3, 5)
        vi = s.get_integrated_intensity(roi, out_signal_axes=(0, 1, 2))
        assert vi.axes_manager.signal_dimension == 3
        assert vi.axes_manager.navigation_dimension == 0
        assert vi.metadata.General.title == "Integrated intensity"
        assert (
            vi.metadata.Diffraction.intergrated_range
            == "CircleROI(cx=3, cy=3, r=5) of Stack of "
        )

    def test_get_integrated_intensity_error(
        self, diffraction_pattern, out_signal_axes=(0, 1, 2)
    ):
        roi = hs.roi.CircleROI(3, 3, 5)
        with pytest.raises(ValueError):
            _ = diffraction_pattern.get_integrated_intensity(roi, out_signal_axes)

    def test_get_integrated_intensity_linescan(self, diffraction_pattern):
        s = diffraction_pattern.inav[0, :]
        s.metadata.General.title = ""
        roi = hs.roi.CircleROI(3, 3, 5)
        vi = s.get_integrated_intensity(roi)
        assert vi.data.shape == (2,)
        assert vi.axes_manager.signal_dimension == 1
        assert vi.axes_manager.navigation_dimension == 0
        assert vi.metadata.Diffraction.intergrated_range == "CircleROI(cx=3, cy=3, r=5)"
