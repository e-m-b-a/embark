import os
import shutil

from django.test import TestCase

from .archiver import archiver
import unittest as ut


class unpacker_test(TestCase):

    def setUp(self):
        self.archiver = archiver

    def test_supported_formats(self):
        expected_formats = ["zip", "tar", "gztar"]

        supported_formats = self.archiver.get_supported_formats()

        for expected_format in expected_formats:
            assert supported_formats.__contains__(expected_format)

    def test_false_file(self):

        archive_name = "invalid.txt"

        # create invalid archive
        f = open(archive_name, "a")
        f.close()

        # check for error
        with self.assertRaises(ValueError):
            self.archiver.unpack(f.name)

        # delete file
        os.remove(archive_name)

    def test_archive_file(self):

        folder_name = "./archive"
        log_names = ["log"+str(i)+".bin" for i in range(10)]

        # create archive
        os.mkdir(folder_name)
        for log_name in log_names:
            log_file = open(folder_name + "/" + log_name, "a")
            log_file.close()

        archiver.pack(folder_name, 'zip', folder_name, '.')

        for log_name in log_names:
            os.remove(folder_name + "/" + log_name)
        os.rmdir(folder_name)

        # unzip archive and assert existance of file
        self.assertTrue(self.archiver.unpack("./archive.zip"))
        for log_name in log_names:
            self.assertTrue(os.path.isfile(log_name))

        # cleanup
        os.remove("./archive.zip")
        for log_name in log_names:
            os.remove(log_name)
