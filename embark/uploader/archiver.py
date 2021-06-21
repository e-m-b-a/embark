import gzip
import logging
import os
import re
import shutil

logger = logging.getLogger('web')


class Archiver:
    """
       Class unpacker
       This class use shutil function to unpack files
    """

    def __init__(self):
        # default formats: zip, tar, gztar, bztar, xztar

        # register additional formats ( gz )
        shutil.register_unpack_format('gz', ['.gz', ], self.gunzip_file)
        pass

    @staticmethod
    def gunzip_file(file_name, work_dir):
        """
            special unzip function for .gz files

            :param file_name: file name of the gz file
            :param work_dir: directory where the archive is located

            :return:
        """

        # see warning about filename
        filename = os.path.split(file_name)[-1]
        filename = re.sub(r"\.gz$", "", filename, flags=re.IGNORECASE)

        # extract .gz file
        with gzip.open(file_name, 'rb') as f_in:
            with open(os.path.join(work_dir, filename), 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    @staticmethod
    def pack(base_name, archive_format, root_dir, base_dir):
        """
            pack function

            :param base_name: name of the file to create, excluding format-specific extension
            :param archive_format: archive format used to pack the directory
            :param root_dir: directory acting as root directory of the archive,
                             all paths in the archive will be relative to it
            :param base_dir: directory archiving is started from, relative to root_dir

            :return: name of archive on success
        """

        # TODO: check location
        return shutil.make_archive(base_name, archive_format, root_dir, base_dir)
        # alternative if single files be zipped:
        # with tarfile

    @staticmethod
    def unpack(file_location, extract_dir=None):
        """
            unpack function
            names non unique, since db takes care of that issue

            :param file_location: file location of the archive
            :param extract_dir: output directory where the archive contents are saved

            :return: True on success, Value error on wrong format, Exception otherwise
        """

        try:
            if extract_dir:
                shutil.unpack_archive(file_location, extract_dir)
            else:
                shutil.unpack_archive(file_location)
            logger.info("Unpacked file successful: %s", file_location)
            return True
        except shutil.ReadError:
            logging.error(f"Format {file_location.split('.', 1)[1]} is not supported")
            raise ValueError
        except Exception as ex:
            logging.error(f"Undefined Error during unpacking file: {file_location}", )
            logging.error(ex)
            raise ex

    @staticmethod
    def get_supported_formats():
        """
            lists all supported formats for unpacking

            :return: enumeration of supported formats as list of strings
        """

        return [name for (name, extensions, description) in shutil.get_unpack_formats()]

    @staticmethod
    def get_supported_extensions():
        """
            list all supported extensions for unpacking

            :return: enumeration of supported extensions as list of strings
        """

        extensions_list = [extensions for (name, extensions, description) in shutil.get_unpack_formats()]
        flat_list = [item for sublist in extensions_list for item in sublist]

        return flat_list

    @classmethod
    def check_extensions(cls, file_name):
        """
            checks file for extension integrity

            :param file_name: file to be checked

            :return: True if extension is supported, ValueError otherwise
        """

        for ext in cls.get_supported_extensions():
            if file_name.endswith(ext):
                return True

        logger.info(f"Format for {file_name} is not supported by archiver")
        return False

    @classmethod
    def copy(cls, src, dst):
        """
            copy file from src to dst

            :param src: src file to be copied
            :param dst: location to be copied to

            :return: path on success
        """

        os.makedirs(os.path.dirname(dst), exist_ok=True)
        return shutil.copy(src, dst)
