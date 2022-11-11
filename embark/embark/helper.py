from random import randrange
import os


def rnd_rgb_color():
    """
    Used for html colors ONLY
    """
    result = "rgb("
    for _value in range(2):                         # nosec
        result += str(randrange(255)) + ", "    # nosec
    return result + str(randrange(255)) + ")"   # nosec


def rnd_rgb_full():
    """
    Used for html colors ONLY
    """
    return "rgb(" + str(randrange(255)) + ", " + str(randrange(255)) + ", " + str(randrange(255)) + ", " + "0.2)"   # nosec


def get_size(start_path='.'):
    """
    returns directory size in bytes
    https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size


if __name__ == '__main__':
    print(rnd_rgb_color())
    print(rnd_rgb_full())
