# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""Test a full run of the codes from the command line."""

from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

import maltpynt as mp
import logging
import os
import sys
import glob
import subprocess as sp
import numpy as np

MP_FILE_EXTENSION = mp.io.MP_FILE_EXTENSION

PY2 = sys.version_info[0] == 2
PYX6 = sys.version_info[1] == 6

if PY2 and PYX6:
    import unittest2 as unittest
else:
    import unittest

logging.basicConfig(filename='MP.log', level=logging.DEBUG, filemode='w')
curdir = os.path.abspath(os.path.dirname(__file__))
datadir = os.path.join(curdir, 'data')


class TestFullRun(unittest.TestCase):

    """Test how command lines work.

    Usually considered bad practice, but in this
    case I need to test the full run of the codes, and files depend on each
    other.
    Inspired by http://stackoverflow.com/questions/5387299/python-unittest-testcase-execution-order

    When command line is missing, uses some function calls
    """

    def step00a_scripts_are_installed(self):
        """Test only once that command line scripts are installed correctly."""
        fits_file = os.path.join(datadir, 'monol_testA.evt')
        command = 'MPreadfile {0}'.format(fits_file)
        sp.check_call(command.split())

    def step01_fake_file(self):
        """Test produce a fake event file"""
        fits_file = os.path.join(datadir, 'monol_test_fake.evt')
        mp.fake.main(['-o', fits_file])

    def step02a_load_events(self):
        """Test event file reading."""
        command = '{0} {1} --nproc 2'.format(
            os.path.join(datadir, 'monol_testA.evt'),
            os.path.join(datadir, 'monol_testA_timezero.evt'),
            os.path.join(datadir, 'monol_test_fake.evt'))
        mp.read_events.main(command.split())

    def step02b_load_events(self):
        """Test event file reading."""
        command = '{0}'.format(
            os.path.join(datadir, 'monol_testB.evt'))
        mp.read_events.main(command.split())

    def step02c_load_events_split(self):
        """Test event file reading."""
        command = \
            '{0} -g --noclobber --min-length 0'.format(
                os.path.join(datadir, 'monol_testB.evt'))
        mp.read_events.main(command.split())

    def step02d_load_gtis(self):
        """Test loading of GTIs from FITS files"""
        fits_file = os.path.join(datadir, 'monol_testA.evt')
        mp.read_events.load_gtis(fits_file)

    def step03a_calibrate(self):
        """Test event file calibration."""
        command = '{0} -r {1}'.format(
            os.path.join(datadir, 'monol_testA_ev' + MP_FILE_EXTENSION),
            os.path.join(datadir, 'test.rmf'))
        mp.calibrate.main(command.split())

    def step03b_calibrate(self):
        """Test event file calibration."""
        command = '{0} -r {1} --nproc 2'.format(
            os.path.join(datadir, 'monol_testB_ev' + MP_FILE_EXTENSION),
            os.path.join(datadir, 'test.rmf'))
        mp.calibrate.main(command.split())

    def step04a_lcurve(self):
        """Test light curve production."""
        command = ('{0} {1} -e {2} {3} --safe-interval '
                   '{4} {5}  --nproc 2').format(
            os.path.join(datadir, 'monol_testA_ev_calib' +
                         MP_FILE_EXTENSION),
            os.path.join(datadir, 'monol_testB_ev_calib' +
                         MP_FILE_EXTENSION),
            3, 50, 100, 300)
        mp.lcurve.main(command.split())

    def step04b_lcurve_split(self):
        """Test lc with gti-split option, and reading of split event file"""
        command = '{0} -g'.format(
            os.path.join(datadir, 'monol_testB_ev_0' +
                         MP_FILE_EXTENSION))
        mp.lcurve.main(command.split())

    def step04c_fits_lcurve(self):
        """Test light curves from FITS."""
        lcurve_ftools_orig = os.path.join(datadir, 'lcurveA.fits')
        mp.lcurve.lcurve_from_events(
            os.path.join(datadir,
                         'monol_testA_ev') + MP_FILE_EXTENSION,
            outfile=os.path.join(datadir,
                                 'lcurve_lc'))
        mp.lcurve.lcurve_from_fits(
            lcurve_ftools_orig,
            outfile=os.path.join(datadir,
                                 'lcurve_ftools_lc'))
        lcurve_ftools = os.path.join(datadir,
                                     'lcurve_ftools_lc' +
                                     MP_FILE_EXTENSION)
        lcurve_mp = os.path.join(datadir,
                                 'lcurve_lc' +
                                 MP_FILE_EXTENSION)
        lcdata_mp = mp.io.load_lcurve(lcurve_mp)
        lcdata_ftools = mp.io.load_lcurve(lcurve_ftools)

        lc_mp = lcdata_mp['lc']

        lenmp = len(lc_mp)
        lc_ftools = lcdata_ftools['lc']
        lenftools = len(lc_ftools)
        goodlen = min([lenftools, lenmp])

        diff = lc_mp[:goodlen] - lc_ftools[:goodlen]

        assert np.all(np.abs(diff) <= 1e-3), \
            'Light curve data do not coincide between FITS and MP'

    def step04d_txt_lcurve(self):
        """Test light curves from txt."""
        lcurve_mp = os.path.join(datadir,
                                 'lcurve_lc' +
                                 MP_FILE_EXTENSION)
        lcdata_mp = mp.io.load_lcurve(lcurve_mp)
        lc_mp = lcdata_mp['lc']
        time_mp = lcdata_mp['time']

        lcurve_txt_orig = os.path.join(datadir,
                                       'lcurve_txt_lc.txt')

        mp.io.save_as_ascii([time_mp, lc_mp], lcurve_txt_orig)

        lcurve_txt = os.path.join(datadir,
                                  'lcurve_txt_lc' +
                                  MP_FILE_EXTENSION)
        mp.lcurve.lcurve_from_txt(lcurve_txt_orig,
                                  outfile=lcurve_txt)
        lcdata_txt = mp.io.load_lcurve(lcurve_txt)

        lc_txt = lcdata_txt['lc']

        assert np.all(np.abs(lc_mp - lc_txt) <= 1e-3), \
            'Light curve data do not coincide between txt and MP'

    def step05e_joinlcs(self):
        """Test produce joined light curves."""
        mp.lcurve.join_lightcurves(
            [os.path.join(datadir, 'monol_testA_E3-50_lc') +
             MP_FILE_EXTENSION,
             os.path.join(datadir, 'monol_testB_E3-50_lc') +
             MP_FILE_EXTENSION],
            os.path.join(datadir, 'monol_test_joinlc' +
                         MP_FILE_EXTENSION))

    def step04f_scrunchlcs(self):
        """Test produce scrunched light curves."""
        command = '{0} {1} -o {2}'.format(
            os.path.join(datadir, 'monol_testA_E3-50_lc') +
            MP_FILE_EXTENSION,
            os.path.join(datadir, 'monol_testB_E3-50_lc') +
            MP_FILE_EXTENSION,
            os.path.join(datadir, 'monol_test_scrunchlc') +
            MP_FILE_EXTENSION)
        mp.lcurve.scrunch_main(command.split())

    def step05a_pds(self):
        """Test PDS production."""
        command = \
            '{0} {1} -f 128 --save-dyn -k PDS --norm rms  --nproc 2 '.format(
                os.path.join(datadir, 'monol_testA_E3-50_lc') +
                MP_FILE_EXTENSION,
                os.path.join(datadir, 'monol_testB_E3-50_lc') +
                MP_FILE_EXTENSION)
        mp.fspec.main(command.split())

    def step05b_pds(self):
        """Test PDS production."""
        command = \
            '{0} -f 128 --save-dyn -k PDS --norm rms'.format(
                os.path.join(datadir, 'monol_testA_E3-50_lc') +
                MP_FILE_EXTENSION)
        mp.fspec.main(command.split())

    def step05c_pds_fits(self):
        """Test PDS production with light curves obtained from FITS files."""
        lcurve_ftools = os.path.join(datadir,
                                     'lcurve_ftools_lc' +
                                     MP_FILE_EXTENSION)
        command = '{0} -f 128'.format(lcurve_ftools)
        mp.fspec.main(command.split())

    def step05d_pds_txt(self):
        """Test PDS production with light curves obtained from txt files."""
        lcurve_txt = os.path.join(datadir,
                                  'lcurve_txt_lc' +
                                  MP_FILE_EXTENSION)
        command = '{0} -f 128'.format(lcurve_txt)
        mp.fspec.main(command.split())

    def step05e_cpds(self):
        """Test CPDS production."""
        command = \
            '{0} {1} -f 128 --save-dyn -k CPDS --norm rms -o {2}'.format(
                os.path.join(datadir, 'monol_testA_E3-50_lc') +
                MP_FILE_EXTENSION,
                os.path.join(datadir, 'monol_testB_E3-50_lc') +
                MP_FILE_EXTENSION,
                os.path.join(datadir, 'monol_test_E3-50'))
        mp.fspec.main(command.split())

    def step05f_cpds(self):
        """Test CPDS production."""
        command = \
            ('{0} {1} -f 128 --save-dyn -k '
             'CPDS --norm rms -o {2} --nproc 2').format(
                os.path.join(datadir, 'monol_testA_E3-50_lc') +
                MP_FILE_EXTENSION,
                os.path.join(datadir, 'monol_testB_E3-50_lc') +
                MP_FILE_EXTENSION,
                os.path.join(datadir, 'monol_test_E3-50'))
        mp.fspec.main(command.split())

    def step05g_dumpdynpds(self):
        """Test dump dynamical PDSs."""
        command = '--noplot ' + \
            os.path.join(datadir,
                         'monol_testA_E3-50_pds') + \
            MP_FILE_EXTENSION
        mp.fspec.dumpdyn_main(command.split())

    def step05h_sumpds(self):
        """Test the sum of pdss."""
        mp.sum_fspec.main([
            os.path.join(datadir,
                         'monol_testA_E3-50_pds') + MP_FILE_EXTENSION,
            os.path.join(datadir,
                         'monol_testB_E3-50_pds') + MP_FILE_EXTENSION,
            '-o', os.path.join(datadir,
                               'monol_test_sum' + MP_FILE_EXTENSION)])

    def step05i_dumpdyncpds(self):
        """Test dumping CPDS file."""
        command = '--noplot ' + \
            os.path.join(datadir,
                         'monol_test_E3-50_cpds') + \
            MP_FILE_EXTENSION
        mp.fspec.dumpdyn_main(command.split())

    def step06_lags(self):
        """Test Lag calculations."""
        command = '{0} {1} {2} -o {3}'.format(
            os.path.join(datadir, 'monol_test_E3-50_cpds') +
            MP_FILE_EXTENSION,
            os.path.join(datadir, 'monol_testA_E3-50_pds') +
            MP_FILE_EXTENSION,
            os.path.join(datadir, 'monol_testB_E3-50_pds') +
            MP_FILE_EXTENSION,
            os.path.join(datadir, 'monol_test'))
        mp.lags.main(command.split())

    def step07a_rebinlc(self):
        """Test LC rebinning."""
        command = '{0} -r 2'.format(
            os.path.join(datadir, 'monol_testA_E3-50_lc') +
            MP_FILE_EXTENSION)
        mp.rebin.main(command.split())

    def step07b_rebinpds(self):
        """Test PDS rebinning 1."""
        command = '{0} -r 2'.format(
            os.path.join(datadir, 'monol_testA_E3-50_pds') +
            MP_FILE_EXTENSION)
        mp.rebin.main(command.split())

    def step07c_rebinpds(self):
        """Test geometrical PDS rebinning"""
        command = '{0} -r 1.03'.format(
            os.path.join(datadir, 'monol_testA_E3-50_pds') +
            MP_FILE_EXTENSION)
        mp.rebin.main(command.split())

    def step07d_rebincpds(self):
        """Test CPDS rebinning."""
        command = '{0} -r 2'.format(
            os.path.join(datadir, 'monol_test_E3-50_cpds') +
            MP_FILE_EXTENSION)
        mp.rebin.main(command.split())

    def step07e_rebincpds(self):
        """Test CPDS geometrical rebinning."""
        command = '{0} -r 1.03'.format(
            os.path.join(datadir, 'monol_test_E3-50_cpds') +
            MP_FILE_EXTENSION)
        mp.rebin.main(command.split())

    def step08a_savexspec(self):
        """Test save as Xspec 1."""
        command = '{0}'.format(
            os.path.join(datadir, 'monol_testA_E3-50_pds_rebin2') +
            MP_FILE_EXTENSION)
        mp.save_as_xspec.main(command.split())

    def step08b_savexspec(self):
        """Test save as Xspec 2."""
        command = '{0}'.format(
            os.path.join(datadir, 'monol_testA_E3-50_pds_rebin1.03') +
            MP_FILE_EXTENSION)
        mp.save_as_xspec.main(command.split())

    def step09a_create_gti(self):
        """Test creating a GTI file"""

        fname = os.path.join(datadir, 'monol_testA_E3-50_lc') + \
            MP_FILE_EXTENSION
        command = "{0} -f lc>0 -c --debug".format(fname)
        mp.create_gti.main(command.split())

    def step09b_create_gti(self):
        """Test creating a GTI file"""

        fname = os.path.join(datadir, 'monol_testA_E3-50_gti') + \
            MP_FILE_EXTENSION
        lcfname = os.path.join(datadir, 'monol_testA_E3-50_lc') + \
            MP_FILE_EXTENSION
        command = "{0} -a {1} --debug".format(lcfname, fname)

        mp.create_gti.main(command.split())

    def step10a_readfile(self):
        """Test reading and dumping a MaLTPyNT file"""

        fname = os.path.join(datadir, 'monol_testA_E3-50_gti') + \
            MP_FILE_EXTENSION
        command = "{0}".format(fname)

        mp.io.main(command.split())

    def step10b_readfile(self):
        """Test reading and dumping a FITS file"""

        fitsname = os.path.join(datadir, 'monol_testA.evt')
        command = "{0}".format(fitsname)

        mp.io.main(command.split())

    def step10c_save_as_qdp(self):
        """Test saving arrays in a qdp file"""
        arrays = [np.array([0, 1, 3]), np.array([1, 4, 5])]
        errors = [np.array([1, 1, 1]), np.array([[1, 0.5], [1, 0.5], [1, 1]])]
        mp.io.save_as_qdp(arrays, errors,
                          filename=os.path.join(datadir,
                                                "monol_test_qdp.txt"))

    def step10d_save_as_ascii(self):
        """Test saving arrays in a ascii file"""
        array = np.array([0, 1, 3])
        errors = np.array([1, 1, 1])
        mp.io.save_as_ascii(
            [array, errors],
            filename=os.path.join(datadir, "monol_test.txt"),
            colnames=["array", "err"])

    def step11_exposure(self):
        """Test exposure calculations from unfiltered files"""

        lcname = os.path.join(datadir,
                              'monol_testA_E3-50_lc' + MP_FILE_EXTENSION)
        ufname = os.path.join(datadir, 'monol_testA_uf.evt')
        command = "{0} {1}".format(lcname, ufname)

        mp.exposure.main(command.split())

    def step12_plot(self):
        """Test plotting"""
        pname = os.path.join(datadir, 'monol_testA_E3-50_pds_rebin1.03') + \
            MP_FILE_EXTENSION
        cname = os.path.join(datadir, 'monol_test_E3-50_cpds_rebin1.03') + \
            MP_FILE_EXTENSION
        lname = os.path.join(datadir, 'monol_testA_E3-50_lc') + \
            MP_FILE_EXTENSION
        mp.plot.main([pname, cname, lname, '--noplot'])

    def _all_steps(self):
        for name in sorted(dir(self)):
            if name.startswith("step"):
                yield name, getattr(self, name)

    def test_steps(self):
        """Test a full run of the scripts (command lines)."""
        print('')
        for name, step in self._all_steps():
            try:
                print('- ', step.__doc__, '...', end=' (command line) ')
                step()
                print('OK')
            except Exception as e:
                self.fail("{0} failed ({1}: {2})".format(step, type(e), e))
                print('Failed')
        print('Cleaning up...')

        file_list = \
            glob.glob(os.path.join(datadir,
                                   '*monol_test*')
                      + MP_FILE_EXTENSION) + \
            glob.glob(os.path.join(datadir,
                                   '*lcurve*')
                      + MP_FILE_EXTENSION) + \
            glob.glob(os.path.join(datadir,
                                   '*lcurve*.txt')) + \
            glob.glob(os.path.join(datadir,
                                   '*.log')) + \
            glob.glob(os.path.join(datadir,
                                   '*monol_test*.dat')) + \
            glob.glob(os.path.join(datadir,
                                   '*monol_test*.txt')) + \
            glob.glob(os.path.join(datadir,
                                   'monol_test_fake.evt'))
        for f in file_list:
            os.remove(f)


if __name__ == '__main__':
    unittest.main(verbosity=2)