#!/usr/bin/perl
#script to list all figures used in the *.tex files associated with the Technical Proposal directories
use strict;
use warnings;

#Searching /Users/aheavey/Documents/github-local/dune-tdr/vol-exec/ch-exec-comp-appx.tex
#my $root_dir = '/Users/demuth/DUNE/2018/';                 #change this to match your installation
#my $tex_dir  = 'Technical-Proposal/executive-summary';      #no trailing /

#$root_dir = '/Users/demuth/Work/dune/tdr/201907/dune-tdr/';
#$tex_dir  = 'vol-exec';
my $root_dir = '/Users/aheavey/Documents/github-local/dune-tdr/';
my $tex_dir  = 'vol-exec';

my $i=1;
my $base_dir = $root_dir.$tex_dir;
#print "base_dir=$base_dir\n";
process_files($base_dir);

my $outstr;               #listing of filenames from \includegraphics[]{filename}
my $outfile = "out.csv";  #writes this file to the same directory that this script runs from
open(FH, '>', $outfile) or die $!;
print FH $outstr;
close(FH);

sub process_files {
    my $path = shift;    
    opendir(DIR, $path)
        or die "Unable to open $path: $!";
        
    my @files = grep { !/^\.{1,2}$/ } readdir (DIR);  #load @files array with file names, neglecting those leading in .
    closedir (DIR);
    @files = map { $path . '/'. $_ } @files;          #prepend full path on file name
 
    for (@files) {
        next if $_ =~ m/\.DS\_Store/;   #skip .DS_Store
        next if $_ =~ m/figures/;       #skip figures directory
    
        if (-d $_) {             #if filename is a (sub)directory
            process_files ($_);  #recursive if subdirectories exist
        } else {
            next unless (-f $_);               #skip if DNE
            next unless ($_ =~ m/\.tex$/);     #skip if not .tex
            print "Searching $_\n";
	
            my $j=1;
            my $filename = $_;
            my $ln = 0;
            my $excerpted;
            open (MYFILE, $filename) or die $! ;
            while (<MYFILE>) {
                $ln++;                                #count line number
                chomp;
                next if $_ =~ /^\%/;   #skip if first character in line is % sign (latex comment line)
                $excerpted = $_;
                #$excerpted =~ s/.+?\{(.+?)\}.*/$1/;
                if ( $_ =~ m/\\includegraphics/g )      #locate images in *.tex assuming use of \includegraphics command
                #if ($_ =~ m/^.*?\\includegraphics.*?/g)
                {
                    $excerpted =~ s/.+?\{(.+?)\}.*/$1/;
                    #next if $1 =~ m/\%\\/g;
                    print "$i : $j) $_  ($ln) \n"; #occurance: local_occurance) line (line_number) \n
                    $outstr .= "$excerpted\n";
        			$i++; $j++;
                }
        	}
        	close (MYFILE);
       }
    }
}        

my $k = $i-1;
print "A total of $k image files found in the .tex files located in $base_dir\n\n\n";

exit 0;
#Reference: https://www.perlmonks.org/?node_id=136482
#Code by DeMuth 2018


