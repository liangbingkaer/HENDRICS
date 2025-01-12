import glob
import os
import shutil
from pathlib import Path


def _dummy_par(par, pb=1e20, a1=0.0, f0=1.0):
    with open(par, "w") as fobj:
        print("PSRJ     FAKE_X-1", file=fobj)
        print("RAJ      00:55:01", file=fobj)
        print("DECJ     12:00:40.2", file=fobj)
        print("PEPOCH   560000.0", file=fobj)
        print(f"F0       {f0}", file=fobj)
        print("BINARY   BT", file=fobj)
        print("DM       0", file=fobj)
        print(f"PB       {pb}", file=fobj)
        print(f"A1       {a1}", file=fobj)
        print("OM       0.0", file=fobj)
        print("ECC      0.0", file=fobj)
        print("T0       56000", file=fobj)
        print("EPHEM    DE421", file=fobj)
        print("CLK      TT(TAI)", file=fobj)

    return par


def find_file_pattern_in_dir(pattern, directory):
    return [str(p) for p in Path(directory).glob(pattern)]


def cleanup_test_dir(datadir):
    from hendrics.io import HEN_FILE_EXTENSION

    patterns = [
        "*" + HEN_FILE_EXTENSION,
        "*lcurve*.txt",
        "*monol_test*.dat",
        "*monol_test*.png",
        "*monol_test*.txt",
        "*monol_test_fake*.evt",
        "*bubu*",
        "*.p",
        "*.qdp",
        "*.inf",
        "*.hdf5",
        "*.ecsv",
        "*.csv",
        "*.dat",
    ]

    file_list = []
    for pattern in patterns:
        file_list.extend(find_file_pattern_in_dir(pattern, datadir))

    for f in file_list:
        f = Path(f)
        if f.exists() and not f.is_dir():
            print(f"Removing {f}")
            f.unlink()
        elif f.exists() and f.is_dir():
            print(f"Removing directory {f}")
            shutil.rmtree(str(f))

    patterns = ["*_pds*/", "*_cpds*/", "*_sum/"]

    dir_list = []
    for pattern in patterns:
        dir_list.extend(find_file_pattern_in_dir(pattern, datadir))
    for f in dir_list:
        if Path(f).exists():
            shutil.rmtree(f)
