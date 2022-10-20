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

import traceback

import cv2

from detectron2.data import MetadataCatalog
from fiftyone import ProgressBar
from fiftyone.core.dataset import Dataset

from compressai_vision.conversion.detectron2 import detectron251, findLabels
from compressai_vision.evaluation.pipeline.base import EncoderDecoder


def annexPredictions(  # noqa: C901
    predictor=None,
    fo_dataset: Dataset = None,
    gt_field: str = "detections",
    predictor_field: str = "detectron-predictions",
    encoder_decoder=None,  # compressai_vision.evaluation.pipeline.base.EncoderDecoder
    use_pb: bool = False,  # progressbar.  captures stdion
    use_print: int = 1,  # print progress at each n:th line.  good for batch jobs
):
    """Run detector and EncoderDecoder instance on a dataset.  Append detector results and bits-per-pixel to each sample.

    :param predictor: A Detectron2 predictor
    :param fo_dataset: Fiftyone dataset
    :param gt_field: Which dataset member to use for ground truths.  Default: "detections"
    :param predictor_field: Which dataset member to use for saving the Detectron2 results.  Default: "detectron-predictions"
    :param encoder_decoder: (optional) a ``compressai_vision.evaluation.pipeline.EncoderDecoder`` subclass instance to apply on the image before detection
    :param use_pb: Show progressbar or not.  Nice for interactive runs, not so much for batch jobs.  Default: False.
    :param use_print: Print progress at every n:th. step.  Default: 0 = no printing.
    """
    assert predictor is not None, "provide Detectron2 predictor"
    assert fo_dataset is not None, "provide fiftyone dataset"
    if encoder_decoder is not None:
        assert issubclass(
            encoder_decoder.__class__, EncoderDecoder
        ), "encoder_decoder instances needs to be a subclass of EncoderDecoder"

    model_meta = MetadataCatalog.get(predictor.cfg.DATASETS.TRAIN[0])

    """we don't need this!
    d2_dataset = FO2DetectronDataset(
        fo_dataset=fo_dataset,
        detection_field=detection_field,
        model_catids = model_meta.things_classes,
        )
    """
    try:
        _ = findLabels(fo_dataset, detection_field=gt_field)
    except ValueError:
        print(
            "your ground truths are empty: samples have no member '",
            gt_field,
            "' will set allowed_labels to empty list",
        )
        # allowed_labels = []

    # use open image ids if avail
    if fo_dataset.get_field("open_images_id"):
        id_field_name = "open_images_id"
    else:
        id_field_name = "id"

    npix_sum = 0
    nbits_sum = 0
    cc = 0
    # with ProgressBar(fo_dataset) as pb: # captures stdout
    if use_pb:
        pb = ProgressBar(fo_dataset)
    for sample in fo_dataset:
        cc += 1
        # sample.filepath
        path = sample.filepath
        im = cv2.imread(path)
        if im is None:
            print("FATAL: could not read the image file '" + path + "'")
            return -1
        # tag = path.split(os.path.sep)[-1].split(".")[0]  # i.e.: /path/to/some.jpg --> some.jpg --> some
        # if open_images_id is avail, then use it, otherwise use normal id
        tag = sample[id_field_name]
        if encoder_decoder is not None:
            # before using a detector, crunch through
            # encoder/decoder
            try:
                nbits, im_ = encoder_decoder.BGR(
                    im, tag=tag
                )  # include a tag for cases where EncoderDecoder uses caching
            except Exception as e:
                print("EncoderDecoder failed with '" + str(e) + "'")
                print("Traceback:")
                traceback.print_exc()
                return -1
            if nbits < 0:
                # there's something wrong with the encoder/decoder process
                # say, corrupt data from the VTMEncode bitstream etc.
                print("EncoderDecoder returned error: will try using it once again")
                nbits, im_ = encoder_decoder.BGR(im, tag=tag)
            if nbits < 0:
                print("EncoderDecoder returned error - again!  Will abort calculation")
                return -1

            # NOTE: use tranformed image im_
            npix_sum += im_.shape[0] * im_.shape[1]
            nbits_sum += nbits
        else:
            im_ = im

        res = predictor(im_)

        predictions = detectron251(
            res,
            model_catids=model_meta.thing_classes,
            # allowed_labels=allowed_labels # not needed, really
        )  # --> fiftyone Detections object

        """# could save nbits into each sample:
        if encoder_decoder is not None:
            predictions.nbits = nbits
        """
        sample[predictor_field] = predictions

        sample.save()
        if use_pb:
            pb.update()
        # print(">>>", cc%use_print)
        if use_print > 0 and ((cc % use_print) == 0):
            print("sample: ", cc, "/", len(fo_dataset))
    if use_pb:
        pb.close()

    # calculate bpp as defined by the VCM working group:
    if npix_sum < 1:
        if encoder_decoder:  # alert user if EncoderDecoder class was requested
            print("error: number of pixels sum < 1")
            return -1
        return None
    if nbits_sum < 1:
        if encoder_decoder:  # alert user if EncoderDecoder class was requested
            print("error: number of bits sum < 1")
            return -1
        return None
    bpp = nbits_sum / npix_sum
    return bpp
