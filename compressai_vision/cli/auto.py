# Copyright (c) 2022, InterDigital Communications, Inc
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted (subject to the limitations in the disclaimer
# below) provided that the following conditions are met:

# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * Neither the name of InterDigital Communications, Inc nor the names of its
#   contributors may be used to endorse or promote products derived from this
#   software without specific prior written permission.

# NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY
# THIS LICENSE. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""cli : Command-line interface tools for compressai-vision
"""
import os
import sys

# define legit filenames.. there are inconsistencies here
fname_list = [
    "detection_validation_input_5k.lst",
    "detection_validation_5k_bbox.csv",  # inconsistent name
    "detection_validation_labels_5k.csv",
    "segmentation_validation_input_5k.lst",
    "segmentation_validation_bbox_5k.csv",
    "segmentation_validation_labels_5k.csv",
    "segmentation_validation_masks_5k.csv",
]

help_st = """
compressai-mpeg_vcm-auto-import

parameters:

    --datadir=/path/to/datasets     directory where all datasets are downloaded by default (optional)

Automatic downloading of images and importing files provided by MPEG/VCM test conditions into fiftyone

Before running this command, put the following files into the same directory
(please note 'detection_validation_5k_bbox.csv' name inconsistency):

"""
for fname in fname_list:
    help_st += fname + "\n"
help_st += "\n"


class Namespace:
    pass


def get_(key):
    """So that we use only legit names"""
    return fname_list[fname_list.index(key)]


def get_inp(inp_, txt=""):
    """Ask user for input, provide default input"""
    input_ = input("Give " + txt + " [" + inp_ + "]: ")
    if len(input_) < 1:
        # user just pressed enter
        input_ = inp_  # use the default path
    return input_


def get_dir(dir_, txt="", make=True, check=False):
    """Ask the user for a path.  Give also a default path"""
    dir_input = input("Give " + txt + " [" + dir_ + "]: ")
    if len(dir_input) < 1:
        # user just pressed enter
        dir_input = dir_  # use the default path
    if make:
        os.makedirs(dir_input, exist_ok=True)
    elif check:
        basepath = os.path.sep.join(
            dir_input.split(os.path.sep)[0:-1]
        )  # remove last bit of the path
        assert os.path.isdir(basepath), "path " + basepath + " does not exit"
    return dir_input


def main():
    from compressai_vision.cli import convert_mpeg_to_oiv6, download, dummy, register

    args = []
    dirname = None
    if len(sys.argv) > 1:
        if sys.argv[1] in ["MOCK"]:  # some debugging cli parameters are allowed
            args = sys.argv[1]
        elif "--datadir=" in sys.argv[1]:
            dirname = (
                sys.argv[1].split("=")[1].strip()
            )  # --datadir=/path/to --> /path/to
            print("WARNING: using datadir", dirname)
            assert os.path.isdir(dirname), "no such directory " + dirname
        else:
            print(help_st)
            return

    for fname in fname_list:
        if not os.path.exists(fname):
            print("\nFATAL: missing file", fname)
            print(help_st)
            sys.exit(2)

    p = Namespace()
    if "MOCK" in args:
        print("WARNING: MOCK TEST")
        p.mock = True
    else:
        p.mock = False
    p.y = False
    p.dataset_name = "open-images-v6"

    if dirname is None:
        dir_ = os.path.join(
            "~", "fiftyone", p.dataset_name
        )  # ~/fiftyone/open-images-v6
    else:
        dir_ = os.path.join(dirname, p.dataset_name)

    dir_ = get_dir(dir_, "path to download (MPEG/VCM subset of) OpenImageV6 ")
    source_dir = os.path.join(
        dir_, "validation"
    )  # "~/fiftyone/open-images-v6/validation"

    print("\n**DOWNLOADING**\n")
    p.lists = (
        get_("detection_validation_input_5k.lst")
        + ","
        + get_("segmentation_validation_input_5k.lst")
    )
    p.split = "validation"
    p.dir = dir_
    download(p)

    print("\n**CONVERTING MPEG/VCM DETECTION DATA TO OPENIMAGEV6 FORMAT**\n")
    p = Namespace()
    p.y = False

    if dirname is None:
        mpeg_vcm_dir = os.path.join(
            "~", "fiftyone", "mpeg_vcm-detection"
        )  # ~/fiftyone/mpeg_vcm-detection
    else:
        mpeg_vcm_dir = os.path.join(dirname, "mpeg_vcm-detection")
    mpeg_vcm_dir = get_dir(
        mpeg_vcm_dir, "imported detection dataset path", make=False, check=False
    )

    p.lists = get_("detection_validation_input_5k.lst")
    # p.dir = "~/fiftyone/open-images-v6/validation"
    p.dir = source_dir
    # p.target_dir = "~/fiftyone/mpeg_vcm-detection"
    p.target_dir = mpeg_vcm_dir
    p.label = get_("detection_validation_labels_5k.csv")
    p.bbox = get_("detection_validation_5k_bbox.csv")
    p.mask = None
    convert_mpeg_to_oiv6(p)

    print("\n**CONVERTING MPEG/VCM SEGMENTATION DATA TO OPENIMAGEV6 FORMAT**\n")
    p = Namespace()
    p.y = False

    if dirname is None:
        mpeg_vcm_dir_seg = os.path.join(
            "~", "fiftyone", "mpeg_vcm-segmentation"
        )  # ~/fiftyone/mpeg_vcm-segmentation
    else:
        mpeg_vcm_dir_seg = os.path.join(dirname, "mpeg_vcm-segmentation")
    mpeg_vcm_dir_seg = get_dir(
        mpeg_vcm_dir_seg, "imported segmentation dataset path", make=False, check=False
    )

    p.lists = get_("segmentation_validation_input_5k.lst")
    # p.dir = "~/fiftyone/open-images-v6/validation"
    p.dir = source_dir
    # p.target_dir = "~/fiftyone/mpeg_vcm-segmentation"
    p.target_dir = mpeg_vcm_dir_seg
    p.label = get_("segmentation_validation_labels_5k.csv")
    p.bbox = get_("segmentation_validation_bbox_5k.csv")
    p.mask = get_("segmentation_validation_masks_5k.csv")
    convert_mpeg_to_oiv6(p)

    print("\n**REGISTERING MPEG/VCM DETECTION DATA INTO FIFTYONE**\n")
    p = Namespace()
    p.y = False
    dataset_name = get_inp("mpeg-vcm-detection", "name for detection dataset")
    p.dataset_name = dataset_name
    p.lists = get_("detection_validation_input_5k.lst")
    p.dir = mpeg_vcm_dir
    p.type = "OpenImagesV6Dataset"
    register(p)

    print("\n**CREATING DUMMY/MOCK DETECTION DATA FOR YOUR CONVENIENCE SIR**\n")
    p = Namespace()
    p.y = False
    p.dataset_name = dataset_name
    dummy(p)

    print("\n**REGISTERING MPEG/VCM SEGMENTATION DATA INTO FIFTYONE**\n")
    p = Namespace()
    p.y = False
    dataset_name = get_inp("mpeg-vcm-segmentation", "name for segmentation dataset")
    p.dataset_name = dataset_name
    p.lists = get_("segmentation_validation_input_5k.lst")
    p.dir = mpeg_vcm_dir_seg
    p.type = "OpenImagesV6Dataset"
    register(p)
    print("\nPlease continue with the compressai-vision command line tool\n")
    print("\nGOODBYE\n")


if __name__ == "__main__":
    main()
