#!/usr/bin/env bash
#
# tests an evaluation pipeline with a compression model from Compressai and
# object detection using detectron2
set -e

echo
echo 14
echo

compressai-vision detectron2-eval --y --dataset-name=oiv6-mpeg-detection-v1-dummy \
--scale=100 \
--progress=1 \
--compressai-model-name=bmshj2018-factorized \
--qpars=1 \
--gt-field=detections \
--output=detectron2_seg_test.json \
--model=COCO-InstanceSegmentation/mask_rcnn_X_101_32x8d_FPN_3x.yaml
