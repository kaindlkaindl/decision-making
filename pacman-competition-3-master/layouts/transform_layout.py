import argparse
import typing


def check_transformation_str(value):
    bag = set(value)
    if bag == set('tm'):
        return value
    raise argparse.ArgumentTypeError("""Transformation strings should only contain 't' and 'm'.""")

def parse_arguments():
    """
    Parse command line arguments, and provide text for --help.
    """
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("original_layout",
                        type=argparse.FileType('r', encoding='utf-8'),
                        help="""The input file""")
    parser.add_argument("result_layout",
                        type=argparse.FileType('w', encoding='utf-8'),
                        help="""The output file.""")
    parser.add_argument("transformations", type=check_transformation_str,
                        help="""A string that indicates the sequence of
                        transformations to perform on a layout. The leftmost
                        operation occurs first. Supported transformations:

                        - t: transpose;
                        - m: mirror.

                        For rotating a map 90 degrees, one can use "tm".""")
    # parser.add_argument('-t', '--transpose', default=False, action='store_true',
    #                     help="""Transposes the input file. If both -t and -m are provided,
    #                     the map will first be transposed, and then mirrored.""")
    # parser.add_argument('-m', '--mirror', default=False, action='store_true',
    #                     help="""Mirrors the input file. If both -t and -m are provided,
    #                     the map will first be transposed, and then mirrored.""")
    return parser.parse_args()


def get_dimensions(lines: typing.List[str]) -> (int, int):
    height = len(lines)
    while not len(lines[-1]):
        height -= 1
        del lines[-1]
    width = max(map(lambda line: len(line), lines))
    return width, height


def transpose(lines: typing.List[str]) -> typing.List[str]:
    width, height = get_dimensions(lines)
    transposed_canvas = []
    result = []
    for _ in range(width):
        transposed_canvas.append(height * [' '])

    for x, line in enumerate(lines):
        for y, char in enumerate(line):
            if char != '\n':
                transposed_canvas[y][x] = char
    for i, row in enumerate(transposed_canvas):
        line = ''.join(row)
        if line.rstrip() or i < width-1:
            result.append(''.join(line) + '\n')
    # Remove trailing \n
    result[-1] = result[-1][:-1]
    return result


def mirror(lines: typing.List[str]) -> typing.List[str]:
    width, _ = get_dimensions(lines)
    result = []
    for line in lines:
        padding = width - len(line)
        if padding:
            line += padding * ' '
        result.append(line[-2::-1] + '\n')
    # Remove trailing \n
    result[-1] = result[-1][:-1]
    return result


if __name__ == "__main__":
    args = parse_arguments()
    layout = args.original_layout.readlines()
    for transformation in args.transformations:
        if transformation == 't':
            layout = transpose(layout)
        elif transformation == 'm':
            layout = mirror(layout)
    args.result_layout.write(''.join(layout))
