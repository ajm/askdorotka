#!/bin/bash
set -e

if [[ $# != 1 ]]; then
    echo "Usage: $0 <VOC directory>"
    exit -1
fi

rm -f test.db
python manage.py validate
python manage.py syncdb

echo
echo "populating database: this might take a while..."
sleep 3
python manage.py populate $1/VOC2007/Annotations/

echo
echo "copying images: this might take a while..."
rm -rf images
cp -r $1/VOC2007/JPEGImages images
#touch images/place_images_here

echo
echo "done"

