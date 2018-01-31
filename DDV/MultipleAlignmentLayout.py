from __future__ import print_function, division, absolute_import, \
    with_statement, generators, nested_scopes

import os
import traceback
from datetime import datetime
from math import ceil

from DNASkittleUtils.CommandLineUtils import just_the_name
from DNASkittleUtils.Contigs import read_contigs, Contig
from DDV.TileLayout import hex_to_rgb
from natsort import natsorted

from DDV.TransposonLayout import TransposonLayout


class MultipleAlignmentLayout(TransposonLayout):
    def __init__(self):
        super(MultipleAlignmentLayout, self).__init__()
        self.using_mixed_widths = True  # we are processing all repeat types with different widths


        #### Rasmol 'Amino' Protein colors
        # self.palette['A'] = hex_to_rgb('C8C8C8')
        # self.palette['R'] = hex_to_rgb('145AFF')
        # self.palette['N'] = hex_to_rgb('00DCDC')
        # self.palette['D'] = hex_to_rgb('E60A0A')
        # self.palette['B'] = hex_to_rgb('E6E600')
        # self.palette['C'] = hex_to_rgb('00DCDC')
        # self.palette['E'] = hex_to_rgb('E60A0A')
        # self.palette['Q'] = hex_to_rgb('EBEBEB')
        # self.palette['Z'] = hex_to_rgb('8282D2')
        # self.palette['G'] = hex_to_rgb('0F820F')
        # self.palette['H'] = hex_to_rgb('0F820F')
        # self.palette['I'] = hex_to_rgb('145AFF')
        # self.palette['L'] = hex_to_rgb('E6E600')
        # self.palette['K'] = hex_to_rgb('3232AA')
        # self.palette['M'] = hex_to_rgb('DC9682')
        # self.palette['F'] = hex_to_rgb('FA9600')
        # self.palette['P'] = hex_to_rgb('FA9600')
        # self.palette['S'] = hex_to_rgb('B45AB4')
        # self.palette['T'] = hex_to_rgb('3232AA')
        # self.palette['W'] = hex_to_rgb('0F820F')
        # self.palette['Y'] = hex_to_rgb('FF69B4')
        # self.palette['V'] = hex_to_rgb('FF69B4')
        # self.palette['X'] = hex_to_rgb('FF6100')


        #### Rasmol Shapely Protein colors
        # Assert full Rasmol colors over Nucleotide values (different from TileLayout)
        # self.palette['A'] = hex_to_rgb('8CFF8C')
        # self.palette['R'] = hex_to_rgb('00007C')
        # self.palette['N'] = hex_to_rgb('FF7C70')
        # self.palette['D'] = hex_to_rgb('A00042')
        # self.palette['B'] = hex_to_rgb('FFFF70')
        # self.palette['C'] = hex_to_rgb('FF4C4C')
        # self.palette['E'] = hex_to_rgb('660000')
        # self.palette['Q'] = hex_to_rgb('FFFFFF')
        # self.palette['Z'] = hex_to_rgb('7070FF')
        # self.palette['G'] = hex_to_rgb('004C00')
        # self.palette['H'] = hex_to_rgb('455E45')
        # self.palette['I'] = hex_to_rgb('4747B8')
        # self.palette['L'] = hex_to_rgb('B8A042')
        # self.palette['K'] = hex_to_rgb('534C52')
        # self.palette['M'] = hex_to_rgb('525252')
        # self.palette['F'] = hex_to_rgb('FF7042')
        # self.palette['P'] = hex_to_rgb('B84C00')
        # self.palette['S'] = hex_to_rgb('4F4600')
        # self.palette['T'] = hex_to_rgb('8C704C')
        # self.palette['W'] = hex_to_rgb('FF8CFF')
        # self.palette['Y'] = hex_to_rgb('FF00FF')
        # self.palette['V'] = hex_to_rgb('FF00FF')


    def process_all_alignments(self, input_fasta_folder, output_folder, output_file_name):
        self.origin[1] += self.levels[5].padding  # One full Row of padding for Title
        start_time = datetime.now()
        self.translate_gapped_fastas_to_contigs(input_fasta_folder)
        print("Converted contigs :", datetime.now() - start_time)

        self.initialize_image_by_sequence_dimensions()
        print("Initialized Image:", datetime.now() - start_time, "\n")
        try:  # These try catch statements ensure we get at least some output.  These jobs can take hours
            self.draw_nucleotides()
            print("\nDrew Nucleotides:", datetime.now() - start_time)
        except Exception as e:
            print('Encountered exception while drawing nucleotides:', '\n')
            traceback.print_exc()
        self.output_image(output_folder, output_file_name)
        print("Output Image in:", datetime.now() - start_time)


    def draw_nucleotides(self):
        for contig in self.contigs:
            assert contig.consensus_width, \
                "You must set the consensus_width in order to use this layout"
        self.draw_nucleotides_in_variable_column_width()  # uses self.contigs and self.layout to draw


    def translate_gapped_fastas_to_contigs(self, input_fasta_folder):
        from glob import glob
        self.contigs = []
        for fasta in natsorted(glob(os.path.join(input_fasta_folder, '*.fa*'))):
            species = read_contigs(fasta)
            consensus_width = max([len(x.seq) for x in species])
            block = Contig(just_the_name(fasta),
                           ''.join([x.seq for x in species]),)
            block.consensus_width = consensus_width
            self.contigs.append(block)
        return self.contigs


    def initialize_image_by_sequence_dimensions(self, consensus_width=None, num_lines=None):
        consensus_width = sum([x.consensus_width for x in self.contigs]) // len(self.contigs)
        heights = [len(x.seq) // x.consensus_width for x in self.contigs]
        num_lines = sum(heights)
        self.set_column_height(heights)
        print("Average Width", consensus_width, "Genes", num_lines)
        self.layout_based_on_repeat_size(consensus_width)
        self.image_length = consensus_width * num_lines
        self.prepare_image(self.image_length)
        print("Image is ", self.image.width, "x", self.image.height)

    def contig_json(self):
        return '[]'  # not implemented, but must override base class
    def set_column_height(self, heights):
        average_line_count = int(ceil(sum(heights) / len(heights)))
        self.column_height = average_line_count * 2
