#!/usr/bin/env waf
'''
Usage:

Configure the project giving it an optional "installation" directory:

./waf configure --prefix=/path/to/install

Build the main products (volume PDFs).  You can find them under
build/.

./waf

To include regenerating TeX files from spreadsheets in DUNE DocDB you
must provide DocDB authentication information:

./waf --docdb-password=<thepassword>

The default user is "dune" and that can be changed with --docdb-username=otheruser.

Generate and build per-chapter PDFs.  They are under build/.  You can
also "install" them.

./waf --chapters

Install the main products to the prefix, optionall may include installing chapter PDFs.

./waf install [--chapters]

Generate volume tar files suitable for submission to the arXiv.  You
can also "install" them.

./waf --arxiv

Remove build products from build/ but keep configuration.

./waf clean

Also remove configuration.  You will need to start over to do more.

./waf distclean
'''

import os

APPNAME = 'dune-tdr'
VERSION = '0.0'
top='.'

# "top-level" reqs/spec names
TOP_LEVEL_SPECS = ('SP-FD',)

def options(opt):
    opt.load('tex')
    opt.add_option('--debug', default=False, action='store_true',
                   help="run pdfLaTeX so that it goes into interactive mode on error.")
    opt.add_option('--chapters', default=False, action='store_true',
                   help="generate and build per-chapter PDFs")
    opt.add_option('--arxiv', default=False, action='store_true',
                   help="make a tarbal for each volume suitable for upload to arXiv")
    opt.add_option('--docdb-username', default="dune",
                   help='The DocDB user name for downloading the requirements spreadsheets.')
    opt.add_option('--docdb-password', default="",
                   help='The DocDB password for downloading requirements spreadsheets.')
    opt.add_option('--docdb-password-file', default="",
                   help='A file holding the DocDB password for downloading requirements spreadsheets.')

def configure(cfg):
    cfg.load('tex')
    cfg.find_program('chapters.sh', var='CHAPTERS',
                     path_list=[os.path.join(os.path.realpath("."),"util")],
                     mandatory = True)

    # To automate requirements table generation some special programs are needed.  They are optional
    cfg.find_program('dune-reqs', var='DUNEREQS',
                     mandatory = False);
    cfg.find_program('dunegen.sh', var='DUNEGEN',
                     path_list=[os.path.join(os.path.realpath("."),"util")],
                     mandatory = False)

    cfg.env.PDFLATEXFLAGS += [ "-file-line-error", "-recorder", ]

def nice_path(node):
    return node.path_from(node.ctx.launch_node())

# it's stuff like this, abyss:
# https://www.phy.bnl.gov/~bviren/pub/topics/waf-latex-arxiv/
# staring back at me.
import tarfile
def tarball(task):
    bld = task.generator.bld
    prefix, extra = task.generator.prefix, task.generator.extra

    globs = task.inputs[0].read() + ' ' + extra
    nodes = bld.path.ant_glob(globs)

    tfname = task.outputs[0].abspath()
    ext = os.path.splitext(tfname)[1][1:]
    with tarfile.open(tfname, 'w:'+ext, ) as tf:
        for node in nodes:
            tar_path = nice_path(node)
            if node.is_bld():
                tar_path = node.bldpath()
            tf.add(nice_path(node), prefix + tar_path)


from waflib.TaskGen import feature, after_method, before_method
@feature('tex') 
@after_method('apply_tex') 
def create_another_task(self): 
    tex_task = self.tasks[-1] 
    doc = tex_task.outputs[0]
    man = os.path.splitext(str(doc))[0] + '.manifest'
    man_node = self.bld.path.find_or_declare(man)
    at = self.create_task('manifest', tex_task.outputs, man_node) 
    #at.outputs.append(man_node)
    # make tex task info available to manifest task
    at.tex_task = tex_task 
    # rebuild whenever the tex task is rebuilt 
    at.dep_nodes.extend(tex_task.outputs)
    # There is an, apparently harmless, warning about the .manifest
    # file being created more than once, and by the same task
    # generator.  This suppresses the error message.
    at.no_errcheck_out = True

from waflib.Task import Task
class manifest(Task):
    def run(self):
        man_node = self.outputs[0]
        self.outputs.append(man_node)
        idx = self.tex_task.uid() 
        nodes = self.generator.bld.node_deps[idx]
        with open(man_node.abspath(), 'w') as fp:
            for node in nodes:
                fp.write(nice_path(node) + '\n')
    

def spreadsheet_updater(bld):
    secret = bld.options.docdb_password
    if not secret and bld.options.docdb_password_file:
        secret = bld.path.find_resource(bld.options.docdb_password_file).read().strip()
    if not secret:
        print ('Note: no --docdb-password[-file] given, spreadsheets will not be updated.')
        return None
    username = bld.options.docdb_username

    docids_node = bld.path.find_resource("util/dune-reqs-docids.txt")

    def ssup(name, docid, docver=""):
        rule="${DUNEREQS} getdocdb -t ${TGT}"
        if docver:
            rule += " -V %s" % docver
        docid_tagfile = "%s.docid"%name
        rule += " -U dune -U %s -P %s -a tar %s"%(username, secret, docid)
        if bld.options.debug:
            print(rule)
        bld(rule=rule,
            source=docids_node,
            target=docid_tagfile)
        return docid_tagfile
    return ssup

def regenerate(bld):
    '''
    Make tasks to regenerate files from "requirements" spreadsheets. 
    '''
    reqsdeps = list()
    if not bld.env['DUNEREQS']:
        print ("Note: dune-reqs not found, will not try to rebuild requirements files")
        return reqsdeps
    
    ssup = spreadsheet_updater(bld)
    if ssup is None:
        return reqsdeps

    # Despite knowing better, generate into the source directory.
    gen_dir = bld.srcnode.make_node('generated')
    reqdefs = gen_dir.make_node('reqdefs.tex')
    reqdefs.write('% generated file, do not edit','w')

    docids_node = bld.path.find_resource("util/dune-reqs-docids.txt")

    for line in docids_node.read().split('\n'):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts=line.split()
        if len(parts) == 3:
            name,docid,docver = parts
        else:
            name,docid = parts
            docver=""

        docid_tagfile = ssup(name,docid,docver)

        # Make individual per-spec row files and a roll-up table for
        # just each "category".
        one_tmpl = bld.path.find_resource("util/templates/spec-longtable-row.tex.j2")
        all_tmpl = bld.path.find_resource("util/templates/spec-longtable-rows.tex.j2")
        one_file = "req-%s-{ssid:02d}.tex"%name
        all_targ = gen_dir.make_node("req-just-%s.tex"%name)
        reqsdeps.append(all_targ)
        bld(rule="${DUNEGEN} reqs-one-and-all %s ${SRC} %s ${TGT}"%(name, one_file),
            source=[docid_tagfile,
                    one_tmpl, all_tmpl],
            target=[all_targ])

        # Make individual per-spec tables files and a pointless roll-up.
        # just each "category".
        one_tmpl = bld.path.find_resource("util/templates/spec-longtable-per.tex.j2")
        all_tmpl = bld.path.find_resource("util/templates/spec-table-all.tex.j2")
        one_file = "req-%s-{label}.tex"%name
        all_targ = gen_dir.make_node("req-perall-%s.tex"%name)
        reqsdeps.append(all_targ)
        bld(rule="${DUNEGEN} reqs-one-and-all %s ${SRC} %s ${TGT}"%(name, one_file),
            source=[docid_tagfile,
                    one_tmpl, all_tmpl],
            target=[all_targ])

        # This one generates a longtable for each category/chapter
        # that includes any "top level" specs.
        # Fixme: this currently will break once DP-FD is a thing.
        tmpl = bld.path.find_resource("util/templates/spec-longtable.tex.j2")
        out = gen_dir.make_node("req-longtable-%s.tex"%name)
        bld(rule="${DUNEGEN} reqs %s ${SRC} ${TGT}"%(name,),
            source=[docid_tagfile, tmpl],
            target=[out])


        # This one generates defs
        tmpl = bld.path.find_resource("util/templates/reqdefs.tex.j2")
        out = gen_dir.make_node("reqdefs-%s.tex"%name)
        reqdefs.write('\\input{generated/%s}\n' % out.name[:-4], 'a')
        reqsdeps.append(out)
        bld(rule="${DUNEGEN} reqs %s ${SRC} ${TGT}"%(name,),
            source=[docid_tagfile, tmpl],
            target=[out])


    return reqsdeps


def build(bld):


    prompt_level = 0
    if bld.options.debug:
        prompt_level = 1


    # First, if we are so configured then try rebuild things from the "requirements" spreadsheets.
    reqsdeps = regenerate(bld)        


    chaptex = bld.path.find_resource("util/chapters.tex")

    # explicitly order them here to get a volnum for the per-chapter generation
    voltexs = [
        "vol-exec.tex",
        "vol-physics.tex",
        "vol-sp.tex",
        "vol-dp.tex",
        "vol-nd.tex",
        "vol-swc.tex",
        "vol-tc.tex",
#        "vol-spec.tex"
    ]
    

    maintexs = list()
    for volind, voltex in enumerate(voltexs):
        volnode = bld.path.find_resource(voltex)
        volname = voltex.replace('.tex','')
        voldir = bld.path.find_dir(volname)
        volpdf = bld.path.find_or_declare(volname + '.pdf')
        voltar = bld.path.find_or_declare('%s-%s.tar.gz' % (volname, VERSION))
        volman = bld.path.find_or_declare(volname + '.manifest')
        maintexs.append(volnode)

        # Task to build the volume
        bld(features='tex',
            prompt = prompt_level,
            type = 'pdflatex',
            source = [volnode],
            target = volpdf.name)
        #for reqnode in reqsdeps:
        #    bld.add_manual_dependency(volnode, reqnode)
        bld.install_files('${PREFIX}', [volpdf])
        
        
        # Tasks to build per chapter
        if bld.options.chapters:
            for chtex in voldir.ant_glob("ch-*.tex"):
                chname = os.path.basename(chtex.name).replace('.tex','')
                chmaintex = bld.path.find_or_declare("%s-%s.tex" % (volname, chname))
                chmainpdf = bld.path.find_or_declare("%s-%s.pdf" % (volname, chname))
                maintexs.append(chmaintex)
                bld(source=[chaptex, chtex],
                    target=chmaintex.name,
                    rule="${CHAPTERS} ${SRC} ${TGT} '%s' '%s' %d" % (volname, chname, volind+1))

                bld(features='tex',
                    prompt = prompt_level,
                    source = chmaintex,
                    # name target as file name so can use --targets w/out full path
                    target = chmainpdf.name)

                bld.install_files('${PREFIX}/%s'%volname,
                                  chmaintex.change_ext('.pdf', '.tex'))

        if bld.options.arxiv:
            bld(source=[volman, voltex],
                target=[voltar],
                prefix = '%s-%s-%s/' % (APPNAME, volname, VERSION),
                extra = voltex + ' utphys.bst dune.cls graphics/dunelogo_colorhoriz.jpg',
                rule=tarball)
            bld.install_files('${PREFIX}', [voltar])


    #assert len(maintexs) == len(set(maintexs))
    #print (maintexs)
    #print (reqsdeps)
