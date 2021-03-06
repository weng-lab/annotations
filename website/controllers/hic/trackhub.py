#!/usr/bin/env python

import os
import sys
import json
import StringIO

from helpers_trackhub import Track, PredictionTrack, BigGenePredTrack, BigWigTrack, officialVistaTrack, bigWigFilters, BIB5, TempWrap

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from models.hic.web_epigenomes import WebEpigenome

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../metadata/utils'))
from utils import Utils
from files_and_paths import Dirs


class TrackHub:
    def __init__(self, args, epigenomes, urlStatus, row):
        self.args = args
        self.epigenomes = epigenomes
        self.urlStatus = urlStatus
        self.assembly = row[0]
        self.assays = row[1]
        self.tissue_ids = json.loads(row[2])
        self.loci = row[3]
        self.hubNum = row[4]

        self.priority = 1

    def Custom(self):
        lines = []
        #lines += ["browser hide all"]
        #lines += ["browser pack knownGene refGene ensGene"]
        #lines += ["browser dense snp128"]

        f = StringIO.StringIO()
        map(lambda line: f.write(line + "\n"), lines)

        return f.getvalue()

    def ParsePath(self, path):
        if not path:
            raise Exception("no path")

        if 1 == len(path):
            if path[0].startswith("hub_") and path[0].endswith(".txt"):
                return self.makeHub()
            if path[0].startswith("genomes_") and path[0].endswith(".txt"):
                return self.makeGenomes()
            return "ERROR"

        if 2 != len(path):
            raise Exception("path too long")

        if path[0] in ["hg19", "hg38", "mm10"]:
            if path[0] == self.assembly:
                if path[1].startswith("trackDb_") and path[1].endswith(".txt"):
                    return self.makeTrackDb()

        raise Exception("invalid path")

    def makeHub(self):
        f = StringIO.StringIO()
        t = ""
        if self.args.debug:
            t += "debug "
        t += "ENCODE Promoter-like regions" + self.assembly
        for r in [["hub", t],
                  ["shortLabel", t],
                  ["longLabel", t],
                  ["genomesFile", "genomes_{hubNum}.txt".format(hubNum=self.hubNum)],
                  ["email", "zhiping.weng@umassmed.edu"]]:
            f.write(" ".join(r) + "\n")
        return f.getvalue()

    def makeGenomes(self):
        return """genome\t{assembly}
trackDb\t{assembly}/trackDb_{hubNum}.txt""".format(assembly=self.assembly,
                                                   hubNum=self.hubNum)

    def makeTrackDb(self):
        epis = self.epigenomes.GetByAssemblyAndAssays(self.assembly, self.assays)
        epis = filter(lambda e: e.web_id() in self.tissue_ids, epis.epis)

        lines = []
        lines += [self.genes()]

        for wepi in sorted(epis, key=lambda e: e.epi.biosample_term_name):
            if "BothDNaseAndH3K4me3" == self.assays:
                lines += [self.predictionTrackHub(wepi)]
                #lines += [self.compositeTrack(wepi)]
            for exp in wepi.exps():
                try:
                    lines += [self.trackhubExp(exp)]
                except:
                    if self.args.debug:
                        raise
                    pass

        if self.enableVistaTrack():
            lines += [self.vista()]
        lines += [self.phastcons()]

        lines = filter(lambda x: x, lines)

        f = StringIO.StringIO()
        map(lambda line: f.write(line + "\n"), lines)

        return f.getvalue()

    def enableVistaTrack(self):
        if "mm10" == self.assembly:
            for t in self.tissue_ids:
                if "11.5" in t:
                    return True
        return False

    def phastcons(self):
        if "mm10" == self.assembly:
            url = "http://hgdownload.cse.ucsc.edu/goldenPath/mm10/phastCons60way/mm10.60way.phastCons.bw"
        if "hg19" == self.assembly:
            url = "http://hgdownload.cse.ucsc.edu/goldenPath/hg19/phastCons100way/hg19.100way.phastCons.bw"

        desc = "phastCons"

        track = BigWigTrack(desc, self.priority, url, "0,255,0").track()
        self.priority += 1
        return track

    def genes(self):
        if "hg19" == self.assembly:
            return None

        byAssembly = {"mm10": "Comprehensive M8",
                      "hg19": "Comprehensive 24"}
        desc = "GENCODE Genes " + byAssembly[self.assembly]

        byAssemblyURl = {"mm10": os.path.join(BIB5, "genes", "gencode.vM8.annotation.bb"),
                         "hg19": os.path.join(BIB5, "genes", "gencode.v24.annotation.bb")}
        url = byAssemblyURl[self.assembly]

        track = BigGenePredTrack(desc, self.priority, url).track()
        self.priority += 1
        return track

    def vista(self):
        return officialVistaTrack(self.assembly)

    def predictionTrackHub(self, wepi):
        fnp = wepi.predictionFnp()
        if not os.path.exists(fnp):
            return None

        desc = Track.MakeDesc("Promoter-like",
                              wepi.epi.age_display,
                              wepi.epi.biosample_term_name)

        url = os.path.join(BIB5,
                           Dirs.promoterTracksBase,
                           os.path.basename(fnp))

        track = PredictionTrack(desc, self.priority, url).track()
        self.priority += 1
        return track

    def trackhubExp(self, exp):
        url, name, color = self._getUrl(exp, False)

        desc = Track.MakeDesc(name, exp.age, exp.biosample_term_name)

        track = BigWigTrack(desc, self.priority, url, color).track()
        self.priority += 1
        return track

    def _getUrl(self, exp, norm):
        if not exp:
            return None, None, None

        assay = "DNase"
        if exp.isH3K4me3():
            assay = "H3K4me3"

        bigWigs = bigWigFilters(self.assembly, exp.files)

        if not bigWigs:
            raise Exception("missing bigWigs for " + exp.encodeID)
        bigWig = bigWigs[0]

        url = bigWig.url
        if self.urlStatus.find(url) and not self.urlStatus.get(url):
            url = os.path.join(BIB5, "data", bigWig.expID,
                               bigWig.fileID + ".bigWig")

        if norm:
            if "mm10" == self.assembly:
                url = os.path.join(BIB5, "encode_norm", bigWig.expID, bigWig.fileID + ".norm.bigWig")
            else:
                if bigWig.expID.startswith("EN"):
                    url = os.path.join(BIB5, "encode_norm", bigWig.expID, bigWig.fileID + ".norm.bigWig")
                else:
                    url = os.path.join(BIB5, "roadmap_norm/consolidated/",
                                       bigWig.expID,
                                       bigWig.fileID + '-' + assay + ".fc.signal.norm.bigWig")

        if exp.isH3K4me3():
            name = "H3K4me3 Signal"
            color = "18,98,235"
        elif exp.isDNaseSeq():
            name = "DNase Signal"
            color = "255,121,3"
        else:
            raise Exception("unexpected exp")

        return url, name, color

    def compositeTrack(self, wepi):
        dnaseExp, h3k27acExp = wepi.exps()
        h3k27acUrl, h3k27acName, h3k27acColor = self._getUrl(h3k27acExp, True)
        dnaseUrl, dnaseName, dnaseColor = self._getUrl(dnaseExp, True)

        desc = wepi.web_title()
        descShort = desc

        track = """
track composite{priority}
container multiWig
aggregate transparentOverlay
showSubtrackColorOnUi on
type bigWig 0 50.0
maxHeightPixels 128:32:8
shortLabel {descShort}
longLabel {desc}
visibility full
priority {priority}
html examplePage

                track composite{priority}H3K4me3
                bigDataUrl {h3k27acUrl}
                shortLabel H3K4me3
                longLabel H3K4me3
                parent composite{priority}
                type bigWig
                color {h3k27acColor}

                track composite{priority}DNase
                bigDataUrl {dnaseUrl}
                shortLabel DNase
                longLabel DNase
                parent composite{priority}
                type bigWig
                color {dnaseColor}
""".format(priority=self.priority,
           descShort=descShort,
           desc=desc,
           h3k27acUrl=h3k27acUrl,
           h3k27acColor=h3k27acColor,
           dnaseUrl=dnaseUrl,
           dnaseColor=dnaseColor)

        self.priority += 1
        return track

    def showMissing(self):
        wepis = self.epigenomes.GetByAssemblyAndAssays(self.assembly, self.assays)

        def checkUrl(url):
            if not url:
                return {"title": None, "url": None}

            if not self.urlStatus.find(url):
                self.urlStatus.insertOrUpdate(url,
                                              Utils.checkIfUrlExists(url))
            if self.urlStatus.get(url):
                if "encodeproject" in url:
                    return {"title": "OK - ENCODE", "url": url}
                if BIB5 in url:
                    return {"title": "OK - zlab", "url": url}
                if "wustl.edu" in url:
                    return {"title": "OK - roadmap", "url": url}
                return {"title": "OK", "url": url}

            if "encodeproject" in url:
                return {"title": "ERROR - ENCODE", "url": url}
            if BIB5 in url:
                return {"title": "ERROR - zlab", "url": url}
            if "wustl.edu" in url:
                return {"title": "ERROR - roadmap", "url": url}
            return {"title": "ERROR", "url": url}

        def checkExp(exp):
            u, _, _ = self._getUrl(exp, False)
            u = checkUrl(u)
            un, _, _ = self._getUrl(exp, True)
            un = checkUrl(un)
            return u, un

        for wepi in wepis.epis:
            dnaseExp = None
            h3k27acExp = None
            exps = wepi.exps()
            if "BothDNaseAndH3K4me3" == self.assays:
                dnaseExp, h3k27acExp = exps
            if "H3K4me3" == self.assays:
                h3k27acExp = exps[0]
            if "DNase" == self.assays:
                dnaseExp = exps[0]

            desc = wepi.web_title()
            dnaseUrl, dnaseUrlNorm = checkExp(dnaseExp)
            h3k27acUrl, h3k27acUrlNorm = checkExp(h3k27acExp)
            yield(desc, dnaseUrl, dnaseUrlNorm,
                  h3k27acUrl, h3k27acUrlNorm)
