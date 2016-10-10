#!python3
# coding: UTF-8

import sys
import os
import re
import zipfile
import traceback
import configparser
import datetime
import argparse
import importlib
import unittest

from string import Template
from distutils import dir_util, file_util

import dialog_bundled
import compile_rules
import grammalecte.dawg as fsa
from grammalecte.echo import echo
from grammalecte.ibdawg import IBDAWG


class cd:
    """Context manager for changing the current working directory"""
    def __init__ (self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__ (self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__ (self, etype, value, traceback):
        os.chdir(self.savedPath)


def prepareOptions (spfOptions):
    lLine = open(spfOptions, "r", encoding="utf-8").readlines()

    lStructOpt = []
    dOpt = {}
    dOptLabel = {}
    sLang = None

    for s in lLine:
        s = s.rstrip()
        if s.startswith("#"):
            pass
        elif not s:
            pass
        elif s.startswith("["):
            # lang
            sLang = s[1:s.find("=")].strip()
            sLang = sLang[:2]
            dOptLabel[sLang] = {}
        elif re.match(r"\w+:", s):
            # section
            sSection = s[:s.find(":")]
            lLineOptions = s[s.find(":")+1:].split(",")
            for i in range(len(lLineOptions)):
                lLineOptions[i] = lLineOptions[i].strip().split()
                for j in range(len(lLineOptions[i])):
                    sOpt = lLineOptions[i][j]
                    if sOpt.startswith("*"):
                        dOpt[sOpt[1:]] = True
                        lLineOptions[i][j] = sOpt[1:]
                    else:
                        dOpt[sOpt] = False
            lStructOpt.append( (sSection, lLineOptions) )
        elif re.match(r"\w+ *=", s):
            # option label
            sOpt = s[:s.find("=")].strip()
            l = s[s.find("=")+1:].strip().split("\\n")
            if len(l) == 1:
                l.append("")
            dOptLabel[sLang][sOpt] = tuple(l)
        else:
            echo("unknown line:")
            echo(s)
    return { "lStructOpt": lStructOpt, "dOpt": dOpt, "dOptLabel": dOptLabel }


def createOptionsForXPI (dOptData):
    sHTML = ""
    lStructOpt = dOptData['lStructOpt']
    for sSection, lOpt in lStructOpt:
        sHTML += '\n<div id="subsection_' + sSection + '" class="opt_subsection">\n  <h2 data-l10n-id="option_'+sSection+'"></h2>\n'
        for lLineOpt in lOpt:
            for sOpt in lLineOpt:
                sHTML += '  <p><input type="checkbox" id="option_'+sOpt+'" /><label id="option_label_'+sOpt+'" for="option_'+sOpt+'" data-l10n-id="option_'+sOpt+'"></label></p>\n'
        sHTML += '</div>\n'
    
    # Creating translation data
    dProperties = {}
    for sLang in dOptData['dOptLabel'].keys():
        dProperties[sLang] = "\n".join( [ "option_" + sOpt + " = " + dOptData['dOptLabel'][sLang][sOpt][0].replace(" [!]", " [!]")  for sOpt in dOptData['dOptLabel'][sLang] ] )

    return sHTML, dProperties


def createServerOptions (sLang, dOptData):
    with open("server_options."+sLang+".ini", "w", encoding="utf-8") as hDst:
        hDst.write("# Server options. Lang: " + sLang + "\n\n[gc_options]\n")
        for sSection, lOpt in dOptData["lStructOpt"]:
            hDst.write("\n########## " + dOptData["dOptLabel"][sLang].get(sSection, sSection + "[no label found]")[0] + " ##########\n")
            for lLineOpt in lOpt:
                for sOpt in lLineOpt:
                    hDst.write("# " + dOptData["dOptLabel"][sLang].get(sOpt, "[no label found]")[0] + "\n")
                    hDst.write(sOpt + " = " + ("1" if dOptData["dOpt"].get(sOpt, None) else "0") + "\n")
        hDst.write("html = 1\n")


def getConfig (sLang):
    xConfig = configparser.SafeConfigParser()
    try:
        xConfig.read("gc_lang/" + sLang + "/config.ini")
    except:
        print("Config file in project [" + sLang + "] not found")
        return None
    return xConfig


def createOXT (spLang, dVars, dOxt, spLangPack, bInstall):
    "create extension for Writer"
    print("Building extension for Writer")
    spfZip = "_build/" + dVars['name'] + "-"+ dVars['lang'] +"-v" + dVars['version'] + '.oxt'
    hZip = zipfile.ZipFile(spfZip, mode='w', compression = zipfile.ZIP_DEFLATED)

    # Package and parser
    copyGrammalectePackageInZipFile(hZip, spLangPack, dVars['binary_dic'], "pythonpath/")
    hZip.write("cli.py", "pythonpath/cli.py")

    # Extension files
    hZip.writestr("META-INF/manifest.xml", fileFile("gc_core/py/oxt/manifest.xml", dVars))
    hZip.writestr("description.xml", fileFile("gc_core/py/oxt/description.xml", dVars))
    hZip.writestr("Linguistic.xcu", fileFile("gc_core/py/oxt/Linguistic.xcu", dVars))
    hZip.writestr("Grammalecte.py", fileFile("gc_core/py/oxt/Grammalecte.py", dVars))

    for i in dVars["extras"].split(","):
        hZip.writestr(i.strip().replace("../", "").replace("__implname__", dVars["implname"]), \
                      fileFile(spLang + '/' + i.strip(), dVars))

    if "logo" in dVars.keys() and dVars["logo"].strip():
        hZip.write(spLang + '/' + dVars["logo"].strip(), dVars["logo"].strip())

    ## OPTIONS
    # options dialog within LO/OO options panel
    hZip.writestr("pythonpath/lightproof_handler_%s.py" % dVars["implname"], \
                  fileFile("gc_core/py/oxt/lightproof_handler___implname__.py", dVars))
    try:
        d = open(spLang + "/options.txt", "r", encoding="utf-8").readlines()
        dialog_bundled.c(dVars["implname"], d, hZip, dVars["lang"])
    except:
        traceback.print_exc()
        hZip.writestr("pythonpath/lightproof_opts_%s.py" % dVars["implname"], "")
    # new options dialog
    hZip.writestr("pythonpath/Options.py", fileFile("gc_core/py/oxt/Options.py", dVars))
    hZip.write("gc_core/py/oxt/op_strings.py", "pythonpath/op_strings.py")

    ## ADDONS OXT
    print("+ OXT: ", end="")
    for t in dOxt.items():
        print(t[0], end=", ")
        if os.path.isdir(spLang+'/'+t[0]):
            for sf in os.listdir(spLang+'/'+t[0]):
                hZip.write(spLang+'/'+t[0]+"/"+sf, t[1]+"/"+sf)
        else:
            if t[0].startswith('*'):
                hZip.writestr(t[1], fileFile(spLang+'/'+t[0][1:], dVars))
            else:
                hZip.write(spLang+'/'+t[0], t[1])
    print()
    hZip.close()

    # Installation in Writer profile
    if bInstall:
        print("> installation in Writer")
        if dVars.get('unopkg', False):
            cmd = '"'+os.path.abspath(dVars.get('unopkg')+'" add -f '+spfZip)
            print(cmd)
            os.system(cmd)
        else:
            print("# Error: path and filename of unopkg not set in config.ini")


def createFirefoxExtension (sLang, dOptData, sVersion, bLaunchFx=False):
    "create extension for Firefox"
    print("Building extension for Firefox")
    eraseFolder("_build/xpi/"+sLang)
    dir_util.copy_tree("gc_lang/"+sLang+"/xpi/", "_build/xpi/"+sLang)
    dir_util.copy_tree("grammalecte-js", "_build/xpi/"+sLang+"/grammalecte")
    sHTML, dProperties = createOptionsForXPI(dOptData)
    dOptData['optionsHTML'] = sHTML
    dOptData['version'] = sVersion
    copyAndFileTemplate("_build/xpi/"+sLang+"/data/about_panel.html", "_build/xpi/"+sLang+"/data/about_panel.html", dOptData)
    for sLocale in dProperties.keys():
        spfLocale = "_build/xpi/"+sLang+"/locale/"+sLocale+".properties"
        if os.path.exists(spfLocale):
            copyAndFileTemplate(spfLocale, spfLocale, dProperties)
        else:
            echo("Locale file not found: " + spfLocale)
        
    with cd("_build/xpi/"+sLang):
        os.system("jpm xpi")
        if bLaunchFx:
            os.system("jpm run -b nightly")


def createServerZip (sLang, dVars, spLangPack):
    "create server zip"
    spfZip = "_build/" + dVars['name'] + "-"+ dVars['lang'] +"-v" + dVars['version'] + '.zip'
    hZip = zipfile.ZipFile(spfZip, mode='w', compression = zipfile.ZIP_DEFLATED)

    copyGrammalectePackageInZipFile(hZip, spLangPack, dVars['binary_dic'])
    for spf in ["cli.py", "server.py", "bottle.py", "server_options._global.ini", "server_options."+sLang+".ini", \
                "README.md", "LICENSE.txt", "LICENSE.fr.txt"]:
        hZip.write(spf)


def create (sLang, xConfig, bInstallOXT, bJavaScript, bLaunchFx):
    oNow = datetime.datetime.now()
    print("============== MAKE GRAMMALECTE [{0}] at {1.hour:>2} h {1.minute:>2} min {1.second:>2} s ==============".format(sLang, oNow))

    #### READ CONFIGURATION
    print("> read configuration")
    spLang = "gc_lang/" + sLang

    dVars = xConfig._sections['args']
    dVars['locales'] = dVars["locales"].replace("_", "-")
    dVars['loc'] = str(dict([[i, [i[0:2], i[3:5], ""]] for i in dVars["locales"].split(" ")]))
    
    ## COMPILE RULES
    print("> compile rules")
    try:
        lRules = open(spLang + "/rules.grx", 'r', encoding="utf-8").readlines()
    except:
        print("Rules file in project [" + sLang + "] not found")
        return
    dVars.update(compile_rules.make(lRules, dVars['lang'], bJavaScript))
    

    ## READ GRAMMAR CHECKER PLUGINS
    print("PYTHON:")
    print("+ Plugins: ", end="")
    sCodePlugins = ""
    for sf in os.listdir(spLang+"/modules"):
        if re.match(r"gce_\w+[.]py$", sf):
            sCodePlugins += "\n\n" + open(spLang+'/modules/'+sf, "r", encoding="utf-8").read()
            print(sf, end=", ")
    print()
    dVars["plugins"] = sCodePlugins
    dVars["generated"] = open(spLang+"/modules/gc_tmp_eval.py", "r", encoding="utf-8").read()

    ## PREPARE GRAMMAR CHECKER OPTIONS
    dOptData = prepareOptions(spLang + "/options.txt")
    dVars.update(dOptData)
    
    ## CREATE GRAMMAR CHECKER PACKAGE
    spLangPack = "grammalecte/"+sLang
    if not os.path.exists(spLangPack):
        dir_util.mkpath(spLangPack)
    else:
        eraseFolder(spLangPack)
    for sf in os.listdir("gc_core/py"):
        if not os.path.isdir("gc_core/py/"+sf):
            copyAndFileTemplate("gc_core/py/"+sf, spLangPack+"/"+sf, dVars)
    print("+ Modules: ", end="")
    for sf in os.listdir(spLang+"/modules"):
        if not sf.endswith(".tpl.py") and not sf.startswith("gce_") and sf != "gc_tmp_eval.py":
            file_util.copy_file(spLang+"/modules/"+sf, spLangPack)
            print(sf, end=", ")
    print()
    open(spLangPack+"/WARNING.txt", "w", encoding="utf-8").write("The content of this folder is generated by code and replaced at each build.\n")
    
    createServerZip(sLang, dVars, spLangPack)
    createOXT(spLang, dVars, xConfig._sections['oxt'], spLangPack, bInstallOXT)

    ## CREATE SERVER OPTIONS FILE
    createServerOptions(sLang, dOptData)

    #### JAVASCRIPT
    if bJavaScript:
        print("JAVASCRIPT:")
        print("+ Plugins: ", end="")
        sCodePlugins = ""
        for sf in os.listdir(spLang+"/modules-js"):
            if re.match(r"gce_\w+[.]js$", sf):
                sCodePlugins += "\n\n" + open(spLang+'/modules-js/'+sf, "r", encoding="utf-8").read()
                print(sf, end=", ")
        print()
        dVars["pluginsJS"] = sCodePlugins
        dVars["generatedJS"] = open(spLang+"/modules-js/gc_tmp_eval.js", "r", encoding="utf-8").read()

        # options data struct
        dVars["lStructOpt"] = str(dVars["lStructOpt"]).replace("(", "[").replace(")", "]")
        dVars["dOpt"]["html"] = True
        dVars["dOpt"]["esp"] = False
        dVars["dOpt"]["nbsp"] = False
        dVars["dOpt"]["unit"] = False
        dVars["dOpt"]["num"] = False
        dVars["dOpt"] = str(list(dVars["dOpt"].items())).replace("False", "false").replace("True", "true").replace("(", "[").replace(")", "]")
        
        # create folder
        spPack = "grammalecte-js/"+sLang
        if not os.path.exists(spPack):
            dir_util.mkpath(spPack)
        else:
            eraseFolder(spPack)

        # create files
        for sf in os.listdir("gc_core/js"):
            if not os.path.isdir("gc_core/js/"+sf) and sf.startswith("jsex_"):
                dVars[sf[5:-3]] = open("gc_core/js/"+sf, "r", encoding="utf-8").read()
        for sf in os.listdir("gc_core/js"):
            if not os.path.isdir("gc_core/js/"+sf) and sf.startswith("gc_"):
                copyAndFileTemplate("gc_core/js/"+sf, spPack+"/"+sf, dVars)
        print("+ Modules: ", end="")
        for sf in os.listdir(spLang+"/modules-js"):
            if not sf.endswith(".tpl.js") and not sf.startswith("gce_") and sf != "gc_tmp_eval.js":
                copyAndFileTemplate(spLang+"/modules-js/"+sf, spPack+"/"+sf, dVars)
                print(sf, end=", ")
        print()
        open(spPack+"/WARNING.txt", "w", encoding="utf-8").write("The content of this folder is generated by code and replaced at each build.\n")

        createFirefoxExtension(sLang, dOptData, dVars['version'], bLaunchFx)

    return dVars['version']


def copyGrammalectePackageInZipFile (hZip, spPack, sDicName, sAddPath=""):
    for sf in os.listdir("grammalecte"):
        if not os.path.isdir("grammalecte/"+sf):
            hZip.write("grammalecte/"+sf, sAddPath+"grammalecte/"+sf)
    for sf in os.listdir(spPack):
        if not os.path.isdir(spPack+"/"+sf):
            hZip.write(spPack+"/"+sf, sAddPath+spPack+"/"+sf)
    hZip.write("grammalecte/_dictionaries/"+sDicName, sAddPath+"grammalecte/_dictionaries/"+sDicName)


def fileFile (spf, dVars):
    return Template(open(spf, "r", encoding="utf-8").read()).safe_substitute(dVars)


def copyAndFileTemplate (spfSrc, spfDst, dVars):
    s = Template(open(spfSrc, "r", encoding="utf-8").read()).safe_substitute(dVars)
    open(spfDst, "w", encoding="utf-8").write(s)


def unzip (spfZip, sPath, bCreatePath=False):
    if sPath:
        if bCreatePath and not os.path.exists(sPath):
            dir_util.mkpath(sPath)
        print("> unzip in: "+ sPath)
        spInstall = os.path.abspath(sPath)
        if os.path.isdir(spInstall):
            eraseFolder(spInstall)
            with zipfile.ZipFile(spfZip) as zf:
                zf.extractall(sPath)
        else:
            print("# folder not found")


def eraseFolder (sp):
    # recursive!!!
    for sf in os.listdir(sp):
        sf = sp + "/" + sf
        if os.path.isdir(sf):
            eraseFolder(sf)
        else:
            try:
                os.remove(sf)
            except:
                print("%s not removed" % sf)


def main ():
    print("Python: " + sys.version)
    xParser = argparse.ArgumentParser()
    xParser.add_argument("lang", type=str, nargs='+', help="lang project to generate (name of folder in /lang)")
    xParser.add_argument("-b", "--build_data", help="launch build_data.py", action="store_true")
    xParser.add_argument("-d", "--dict", help="generate FSA dictionary", action="store_true")
    xParser.add_argument("-t", "--tests", help="run unit tests", action="store_true")
    xParser.add_argument("-p", "--perf", help="run performance tests", action="store_true")
    xParser.add_argument("-js", "--javascript", help="JavaScript build for Firefox", action="store_true")
    xParser.add_argument("-fx", "--firefox", help="Launch Firefox Nightly for XPI testing", action="store_true")
    xParser.add_argument("-i", "--install", help="install the extension in Writer (path of unopkg must be set in config.ini)", action="store_true")
    xArgs = xParser.parse_args()

    dir_util.mkpath("_build")

    for sLang in xArgs.lang:
        if os.path.exists("gc_lang/"+sLang) and os.path.isdir("gc_lang/"+sLang):
            xConfig = getConfig(sLang)
            dVars = xConfig._sections['args']

            if xArgs.javascript:
                spXPIBuild = "_build/xpi/"+sLang
                dir_util.mkpath(spXPIBuild+"/data")

            # build data
            if xArgs.dict:
                # fsa builder
                oDAWG = fsa.DAWG(dVars['lexicon_src'], dVars['lang_name'], dVars['stemming_method'])
                oDAWG.writeInfo("grammalecte/_dictionaries/" + dVars['binary_dic'] + ".info.txt")
                oDAWG.createBinary("grammalecte/_dictionaries/" + dVars['binary_dic'], int(dVars['fsa_method']))
                if xArgs.javascript:
                    oDic = IBDAWG(dVars['binary_dic'])
                    oDic.writeAsJSObject("gc_lang/"+sLang+"/modules-js/dictionary.js")
            if xArgs.build_data:
                # lang data
                try:
                    build_module = importlib.import_module("gc_lang."+sLang+".build_data")
                except ImportError:
                    print("# Error. Couldn’t import file build_data.py in folder gc_lang/"+sLang)
                else:
                    build_module.main('gc_lang/'+sLang, xArgs.javascript)

            # make
            sVersion = create(sLang, xConfig, xArgs.install, xArgs.javascript, xArgs.firefox)

            # tests
            if xArgs.tests or xArgs.perf:
                print("> Running tests")
                try:
                    tests = importlib.import_module("tests."+sLang+"_test")
                    echo(tests.__file__)
                except ImportError:
                    print("# Error. Couldn't import file {}_test.py in folder tests".format(sLang))
                else:
                    if xArgs.tests:
                        xTestSuite = unittest.TestLoader().loadTestsFromModule(tests)
                        unittest.TextTestRunner().run(xTestSuite)
                    if xArgs.perf:
                        tests.perf(sVersion)
        else:
            print("Folder not found: gc_lang/"+sLang)


if __name__ == '__main__':
    main()
