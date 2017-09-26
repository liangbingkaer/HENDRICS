# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""Search for pulsars."""
from __future__ import (absolute_import, unicode_literals, division,
                        print_function)

from .io import load_events, EFPeriodogram, save_folding, load_folding, \
    HEN_FILE_EXTENSION
from .base import hen_root
from stingray.pulse.search import epoch_folding_search, z_n_search, \
    search_best_peaks, phaseogram
from stingray.pulse.modeling import fit_sinc, fit_gaussian

import numpy as np
import os
import logging
import argparse


class InteractivePhaseogram(object):
    def __init__(self, ev_times, freq, nph=128, nt=128, fdot=0, fddot=0,
                 test=False):
        import matplotlib.pyplot as plt
        from matplotlib.widgets import Slider, Button, RadioButtons

        self.df = 0
        self.dfdot = 0

        self.freq = freq
        self.fdot = fdot
        self.nt = nt
        self.nph = nph
        self.ev_times = ev_times

        self.phaseogr, phases, times, additional_info = \
            phaseogram(ev_times, freq, return_plot=True, nph=nph, nt=nt,
                       fdot=fdot, fddot=fddot, plot=False)
        self.phases, self.times = phases, times
        self.fig, ax = plt.subplots()
        plt.subplots_adjust(left=0.25, bottom=0.30)
        tseg = np.median(np.diff(times))
        tobs = tseg * nt
        delta_df_start = 2 / tobs
        self.df_order_of_mag = np.int(np.log10(delta_df_start))
        delta_df = delta_df_start / 10 ** self.df_order_of_mag

        delta_dfdot_start = 2 / tobs ** 2
        self.dfdot_order_of_mag = np.int(np.log10(delta_dfdot_start))
        delta_dfdot = delta_dfdot_start / 10 ** self.dfdot_order_of_mag

        self.pcolor = plt.pcolormesh(phases, times, self.phaseogr.T,
                                     cmap='magma')
        self.l1, = plt.plot(np.zeros_like(times) + 0.5, times, zorder=10, lw=2,
                            color='w')
        self.l2, = plt.plot(np.ones_like(times), times, zorder=10, lw=2,
                            color='w')
        self.l3, = plt.plot(np.ones_like(times) + 0.5, times, zorder=10, lw=2,
                            color='w')

        plt.xlabel('Phase')
        plt.ylabel('Time')
        plt.colorbar()

        axcolor = 'lightgoldenrodyellow'
        self.axfreq = plt.axes([0.25, 0.1, 0.5, 0.03], facecolor=axcolor)
        self.axfdot = plt.axes([0.25, 0.15, 0.5, 0.03], facecolor=axcolor)
        self.axpepoch = plt.axes([0.25, 0.2, 0.5, 0.03], facecolor=axcolor)

        self.sfreq = Slider(self.axfreq,
                            'Delta freq x$10^{}$'.format(self.df_order_of_mag),
                            -delta_df, delta_df, valinit=self.df)
        self.sfdot = Slider(self.axfdot, 'Delta fdot x$10^{}$'.format(
            self.dfdot_order_of_mag),
                            -delta_dfdot, delta_dfdot, valinit=self.dfdot)
        self.spepoch = Slider(self.axpepoch, 'Delta pepoch',
                              0, times[-1] - times[0], valinit=0)

        self.sfreq.on_changed(self.update)
        self.sfdot.on_changed(self.update)
        self.spepoch.on_changed(self.update)

        self.resetax = plt.axes([0.8, 0.020, 0.1, 0.04])
        self.button = Button(self.resetax, 'Reset', color=axcolor,
                             hovercolor='0.975')

        self.recalcax = plt.axes([0.6, 0.020, 0.1, 0.04])
        self.button_recalc = Button(self.recalcax, 'Recalculate', color=axcolor,
                                    hovercolor='0.975')

        self.button.on_clicked(self.reset)
        self.button_recalc.on_clicked(self.recalculate)

        if not test:
            plt.show()

    def update(self, val):
        fdot = self.sfdot.val * 10 ** self.dfdot_order_of_mag
        freq = self.sfreq.val * 10 ** self.df_order_of_mag
        pepoch = self.spepoch.val + self.times[0]
        delay_fun = lambda times: (times - pepoch) * freq + \
                                  0.5 * (times - pepoch) ** 2 * fdot
        self.l1.set_xdata(0.5 + delay_fun(self.times - self.times[0]))
        self.l2.set_xdata(1 + delay_fun(self.times - self.times[0]))
        self.l3.set_xdata(1.5 + delay_fun(self.times - self.times[0]))

        self.fig.canvas.draw_idle()

    def recalculate(self, event):
        dfdot = self.sfdot.val * 10 ** self.dfdot_order_of_mag
        dfreq = self.sfreq.val * 10 ** self.df_order_of_mag
        pepoch = self.spepoch.val + self.times[0]

        self.fdot = self.fdot - dfdot
        self.freq = self.freq - dfreq

        self.phaseogr, _, _, _ = \
            phaseogram(self.ev_times, self.freq, fdot=self.fdot, plot=False,
                       nph=self.nph, nt=self.nt, pepoch=pepoch)

        self.l1.set_xdata(0.5)
        self.l2.set_xdata(1)
        self.l3.set_xdata(1.5)

        self.sfreq.reset()
        self.sfdot.reset()
        self.spepoch.reset()

        self.pcolor.set_array(self.phaseogr.T.ravel())

        self.fig.canvas.draw()
        print("Frequency is now: {}".format(self.freq))
        print("Fdot is now: {}".format(self.fdot))

    def reset(self, event):
        self.sfreq.reset()
        self.sfdot.reset()
        self.spepoch.reset()
        self.pcolor.set_array(self.phaseogr.T.ravel())
        self.l1.set_xdata(0.5)
        self.l2.set_xdata(1)
        self.l3.set_xdata(1.5)

    def get_values(self):
        return self.freq, self.fdot


def fit(frequencies, stats, center_freq, width=None, obs_length=None,
        baseline=0):
    estimated_amp = stats[np.argmin(np.abs(frequencies - center_freq))]

    if obs_length is not None:
        s = fit_sinc(frequencies, stats - baseline, obs_length=obs_length,
                     amp=estimated_amp, mean=center_freq)
    else:
        df = frequencies[1] - frequencies[0]
        if width is None:
            width = 2 * df
        s = fit_gaussian(frequencies, stats - baseline, width=width,
                         amplitude=estimated_amp, mean=center_freq)

    return s


def folding_search(event_file, fmin, fmax, step=None,
                   func=epoch_folding_search, oversample=2, **kwargs):
    events = load_events(event_file)

    times = (events.time - events.gti[0, 0]).astype(np.float64)
    length = times[-1]

    if step is None:
        step = 1 / oversample / length

    trial_freqs = np.arange(fmin, fmax, step)
    frequencies, stats = func(times, trial_freqs, **kwargs)
    return frequencies, stats, step, length


def run_interactive_phaseogram(event_file, freq, fdot=0, nbin=64, nt=32,
                               test=False):
    events = load_events(event_file)

    times = (events.time - events.gti[0, 0]).astype(np.float64)
    length = times[-1]
    ip = InteractivePhaseogram(times, freq, nph=nbin, nt=nt, fdot=fdot,
                               test=test)

    return ip


def _common_parser(args=None):
    description = ('Search for pulsars using the epoch folding or the Z_n^2 '
                   'algorithm')
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("files", help="List of files", nargs='+')
    parser.add_argument("-f", "--fmin", type=float, required=True,
                        help="Minimum frequency to fold")
    parser.add_argument("-F", "--fmax", type=float, required=True,
                        help="Maximum frequency to fold")
    parser.add_argument('-n', "--nbin", default=128, type=int,
                        help="Number of phase bins of the profile")
    parser.add_argument("--segment-size", default=5000, type=float,
                        help="Size of the event list segment to use (default "
                             "None, implying the whole observation)")
    parser.add_argument("--step", default=None, type=float,
                        help="Step size of the frequency axis. Defaults to "
                             "1/oversample/observ.length. ")
    parser.add_argument("--oversample", default=2, type=float,
                        help="Oversampling factor - frequency resolution "
                             "improvement w.r.t. the standard FFT's "
                             "1/observ.length.")
    parser.add_argument("--expocorr",
                        help="Correct for the exposure of the profile bins. "
                             "This method is *much* slower, but it is useful "
                             "for very slow pulsars, where data gaps due to "
                             "occultation or SAA passages can significantly "
                             "alter the exposure of different profile bins.",
                        default=False, action='store_true')

    parser.add_argument("--find-candidates",
                        help="Find pulsation candidates using thresholding",
                        default=False, action='store_true')
    parser.add_argument("--conflevel", default=99, type=float,
                        help="percent confidence level for thresholding "
                             "[0-100).")

    parser.add_argument("--fit-candidates",
                        help="Fit the candidate peaks in the periodogram",
                        default=False, action='store_true')
    parser.add_argument("--curve", default='sinc', type=str,
                        help="Kind of curve to use (sinc or Gaussian)")
    parser.add_argument("--fit-frequency", type=float,
                        help="Force the candidate frequency to FIT_FREQUENCY")

    parser.add_argument("--debug", help="use DEBUG logging level",
                        default=False, action='store_true')
    parser.add_argument("--loglevel",
                        help=("use given logging level (one between INFO, "
                              "WARNING, ERROR, CRITICAL, DEBUG; "
                              "default:WARNING)"),
                        default='WARNING',
                        type=str)
    # Only relevant to z search
    parser.add_argument('-N', default=2, type=int,
                        help="The number of harmonics to use in the search "
                            "(the 'N' in Z^2_N; only relevant to Z search!)")


    args = parser.parse_args(args)

    if args.debug:
        args.loglevel = 'DEBUG'

    numeric_level = getattr(logging, args.loglevel.upper(), None)
    logging.basicConfig(filename='HENefsearch.log', level=numeric_level,
                        filemode='w')

    return args


def _common_main(args, func):
    args = _common_parser(args)
    files = args.files
    if args.fit_candidates and args.fit_frequency is None:
        args.find_candidates = True
    elif args.fit_candidates and args.fit_frequency is not None:
        args.find_candidates = False
        best_peaks = [args.fit_frequency]

    for i_f, fname in enumerate(files):
        kwargs = {}
        baseline = args.nbin
        kind = 'EF'
        if func == z_n_search:
            kwargs = {'nharm': args.N}
            baseline = args.N
            kind = 'Z2n'
        frequencies, stats, step, length = \
            folding_search(fname, args.fmin, args.fmax, step=args.step,
                           func=func,
                           oversample=args.oversample, nbin=args.nbin,
                           expocorr=args.expocorr,
                           segment_size=args.segment_size, **kwargs)

        efperiodogram = EFPeriodogram(frequencies, stats, kind, args.nbin,
                                      args.N)
        if args.find_candidates:
            threshold = 1 - args.conflevel / 100
            best_peaks, best_stat = \
                search_best_peaks(frequencies, stats, threshold)
            efperiodogram.peaks = best_peaks
            efperiodogram.peak_stat = best_stat
        elif args.fit_frequency is not None:
            efperiodogram.peaks = best_peaks
            efperiodogram.peak_stat = [0]

        if args.fit_candidates:
            search_width = 5 * args.oversample * step
            best_models = []
            for f in best_peaks:
                good = np.abs(frequencies - f) < search_width
                if args.curve.lower() == 'sinc':
                    best_fun = fit(frequencies[good], stats[good], f,
                                   obs_length=length, baseline=baseline)
                elif args.curve.lower() == 'gaussian':
                    best_fun = fit(frequencies[good], stats[good], f,
                                   baseline=baseline)
                else:
                    raise ValueError('`--curve` arg must be sinc or gaussian')

                best_models.append(best_fun)
        efperiodogram.best_fits = best_models

        save_folding(efperiodogram,
                     hen_root(fname) + '_{}'.format(kind) + HEN_FILE_EXTENSION)


def main_efsearch(args=None):
    """Main function called by the `HENefsearch` command line script."""
    _common_main(args, epoch_folding_search)


def main_zsearch(args=None):
    """Main function called by the `HENzsearch` command line script."""
    _common_main(args, z_n_search)


def main_phaseogram(args=None):
    description = ('Plot an interactive phaseogram')
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("file", help="Input event file", type=str)
    parser.add_argument("-f", "--freq", type=float, required=False,
                        help="Initial frequency to fold", default=None)
    parser.add_argument("--fdot", type=float, required=False,
                        help="Initial fdot", default=0)
    parser.add_argument("--periodogram", type=str, required=False,
                        help="Periodogram file", default=None)
    parser.add_argument('-n', "--nbin", default=128, type=int,
                        help="Number of phase bins (X axis) of the profile")
    parser.add_argument("--ntimes", default=64, type=int,
                        help="Number of time bins (Y axis) of the phaseogram")
    parser.add_argument("--debug", help="use DEBUG logging level",
                        default=False, action='store_true')
    parser.add_argument("--test",
                        help="Just a test. Destroys the window immediately",
                        default=False, action='store_true')
    parser.add_argument("--loglevel",
                        help=("use given logging level (one between INFO, "
                              "WARNING, ERROR, CRITICAL, DEBUG; "
                              "default:WARNING)"),
                        default='WARNING',
                        type=str)

    args = parser.parse_args(args)

    if args.debug:
        args.loglevel = 'DEBUG'

    numeric_level = getattr(logging, args.loglevel.upper(), None)
    logging.basicConfig(filename='HENefsearch.log', level=numeric_level,
                        filemode='w')

    if args.periodogram is None and args.freq is None:
        raise ValueError('One of -f or --periodogram arguments MUST be '
                         'specified')
    elif args.periodogram is not None:
        periodogram = load_folding(args.periodogram)
        frequency = periodogram.peaks[0]
        fdot = 0
    else:
        frequency = args.freq
        fdot = args.fdot

    ip = run_interactive_phaseogram(args.file, freq=frequency, fdot=fdot,
                                    nbin=args.nbin, nt=args.ntimes,
                                    test=args.test)

