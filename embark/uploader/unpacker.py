import logging
import shutil


class unpacker:
    """
       Class unpacker
       This class use shutil function to unpack files
    """

    def __init__(self):
        # default formats: zip, tar, gztar, bztar, xztar

        # register additional formats
        # e.g. shutil.register_archive_format(name, function[, extra_args[, description]])

        pass

    @staticmethod
    def unpack(file_location, extract_dir=None):
        """
            unpack function

            :param file_location: file location of the archive
            :param extract_dir: output directory where the archive contents are saved

            :return: Boolean determining status
        """

        try:
            if extract_dir:
                shutil.unpack_archive(file_location, extract_dir)
            else:
                shutil.unpack_archive(file_location)
            logging.debug("Unpacked file successful: %s", file_location)
            return True
        except shutil.ReadError:
            logging.error("Format .%s is not supported", file_location.split(".", 1)[1])
            return False
        except Exception as ex:
            logging.error("Undefined Error during unpacking file: %s", file_location)
            logging.error(ex)
            return False

    @staticmethod
    def get_supported_formats():
        """
            returning supported formats

            :return: list of all supported formats for unpacking
        """

        return [file_format for (file_format, description) in shutil.get_archive_formats()]
