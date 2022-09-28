from random import randrange


def rnd_rgb_color():
    result = "rgb("
    for _n in range(2):
        result += str(randrange(255)) + ", "
    return result + str(randrange(255)) + ")"

if __name__ == '__main__':
    print(rnd_rgb_color())