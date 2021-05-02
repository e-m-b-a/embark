import os
import shutil

from django.test import TestCase

from .unpacker import unpacker
import unittest as ut


class unpacker_test(TestCase):

    def setUp(self):
        self.unpacker = unpacker

    def test_supported_formats(self):
        expected_formats = ["zip", "tar", "gztar"]

        supported_formats = self.unpacker.get_supported_formats()

        for expected_format in expected_formats:
            assert supported_formats.__contains__(expected_format)

    def test_false_file(self):

        archive_name = "invalid.txt"

        # create invalid archive
        f = open(archive_name, "a")
        f.close()

        # check for error
        self.assertFalse(self.unpacker.unpack(f.name))

        # delete file
        os.remove(archive_name)

    def test_archive_file(self):

        folder_name = "./archive"
        image_name = "img.bin"

        # create archive
        os.mkdir(folder_name)
        f = open(folder_name + "/" + image_name, "a")
        f.close()
        shutil.make_archive(folder_name, 'zip', folder_name)
        os.remove(folder_name + "/" + image_name)
        os.rmdir(folder_name)

        # unzip archive and assert existance of file
        self.assertTrue(self.unpacker.unpack("./archive.zip"))
        self.assertTrue(os.path.isfile("img.bin"))

        # cleanup
        os.remove("./archive.zip")
        os.remove("img.bin")
