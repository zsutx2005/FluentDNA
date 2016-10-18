import os
import shutil
import re as regex
import textwrap
from collections import namedtuple

import deepzoom

from PIL import ImageDraw

Batch = namedtuple('Batch', ['chr', 'fastas', 'output_folder'])


class LayoutLevel:
    def __init__(self, name, modulo, chunk_size=None, padding=0, thickness=1, levels=None):
        self.modulo = modulo
        if chunk_size is not None:
            self.chunk_size = chunk_size
            self._padding = padding
            self.thickness = thickness
        else:
            child = levels[-1]
            self.chunk_size = child.modulo * child.chunk_size
            self._padding = 6 * int(3 ** (len(levels) - 2))  # third level (count=2) should be 6, then 18
            last_parallel = levels[-2]
            self.thickness = last_parallel.modulo * last_parallel.thickness + self.padding

    @property
    def padding(self):
        return self._padding

    @padding.setter
    def padding(self, value):
        original_thickness = self.thickness - self._padding
        self._padding = value
        self.thickness = original_thickness + value


class Contig:
    def __init__(self, name, seq, reset_padding, title_padding, tail_padding, title_index, title_length):
        self.name = name
        self.seq = seq
        self.reset_padding = reset_padding
        self.title_padding = title_padding
        self.tail_padding = tail_padding
        self.nuc_title_start = title_index
        self.nuc_seq_start = title_index + title_length



comp = {'A': 'T', 'G': 'C', 'T': 'A', 'C': 'G', 'N': 'N', 'X': 'X'}
def complement(plus_strand):
    return comp[plus_strand]


def rev_comp(plus_strand):
    return ''.join([comp[a] for a in reversed(plus_strand)])


class ReverseComplement:
    def __init__(self, seq):
        """Lazy generator for being able to pull out small reverse complement sections out of large chromosomes"""
        self.seq = seq
        self.length = len(seq)


    def __getitem__(self, key):
        if isinstance(key, slice):
            end = self.length - key.start
            begin = self.length - key.stop
            if end < 0 or begin < 0 or end > self.length:
                raise IndexError("%i %i vs. length %i" % (end, begin, self.length))
            piece = self.seq[begin: end]
            return rev_comp(piece)
        return complement(self.seq[self.length - key - 1])



def multi_line_height(font, multi_line_title, txt):
    sum_line_spacing = ImageDraw.Draw(txt).multiline_textsize(multi_line_title, font)[1]
    descender = font.getsize('y')[1] - font.getsize('A')[1]
    return sum_line_spacing + descender


def pretty_contig_name(contig, title_width, title_lines):
    """Since textwrap.wrap break on whitespace, it's important to make sure there's whitespace
    where there should be.  Contig names don't tend to be pretty."""
    pretty_name = contig.name.replace('_', ' ').replace('|', ' ').replace('chromosome chromosome', 'chromosome')
    pretty_name = regex.sub(r'([^:]*\S):(\S[^:]*)', r'\1: \2', pretty_name)
    pretty_name = regex.sub(r'([^:]*\S):(\S[^:]*)', r'\1: \2', pretty_name)  # don't ask
    if title_width < 20 and len(pretty_name) > title_width * 1.5:  # this is a suboptimal special case to try and
        # cram more characters onto the two lines of the smallest contig titles when there's not enough space
        # For small spaces, cram every last bit into the line labels, there's not much room
        pretty_name = pretty_name[:title_width] + '\n' + pretty_name[title_width:title_width * 2]
    else:  # this is the only case that correctly bottom justifies one line titles
        pretty_name = '\n'.join(textwrap.wrap(pretty_name, title_width)[:title_lines])  # approximate width
    return pretty_name


def copytree(src, dst, symlinks=False, ignore=None):
    if not os.path.exists(dst):
        os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            if not os.path.exists(d) or os.stat(s).st_mtime - os.stat(d).st_mtime > 1:
                shutil.copy2(s, d)


def create_deepzoom_stack(input_image, output_dzi):
    dz_params = {'tile_size': 256,
                 'tile_overlap': 1,
                 'tile_format': "png",
                 'resize_filter': "antialias"}  # cubic bilinear bicubic nearest antialias
    creator = deepzoom.ImageCreator(tile_size=dz_params['tile_size'],
                                    tile_overlap=dz_params['tile_overlap'],
                                    tile_format=dz_params['tile_format'],
                                    resize_filter=dz_params['resize_filter'])
    creator.create(input_image, output_dzi)


def just_the_name(path):
    """Remove extension and path"""
    return os.path.splitext(os.path.basename(path))[0]


def chunks(seq, size):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def pluck_contig(chromosome_name, genome_source):
    """Scan through a genome fasta file looking for a matching contig name.  When it find it, find_contig collects
    the sequence and returns it as a string with no cruft."""
    chromosome_name = '>' + chromosome_name
    print("Searching for", chromosome_name)
    seq_collection = []
    printing = False
    with open(genome_source, 'r') as genome:
        for line in genome.readlines():
            line = line.rstrip()
            if line.startswith('>'):
                # headers.append(line)
                if line == chromosome_name:
                    printing = True
                    print("Found", line)
                elif printing:
                    break  # we've collected all sequence and reached the beginning of the next contig
            elif printing:  # This MUST come after the check for a '>'
                seq_collection.append(line.upper())  # always upper case so equality checks work
    if not len(seq_collection):
        raise FileNotFoundError("Contig not found." + chromosome_name + "   inside " + genome_source)  # File contained these contigs:\n" + '\n'.join(headers)
    return ''.join(seq_collection)


def first_word(string):
    import re
    if '\\' in string:
        string = string[string.rindex('\\') + 1:]
    return re.split('[\W_]+', string)[0]


def make_output_dir_with_suffix(base_path, suffix):
    output_dir = base_path + suffix
    print("Creating Chromosome Output Directory...", os.path.basename(output_dir))
    os.makedirs(output_dir, exist_ok=True)
    return output_dir