import re
import requests
import time
from nala.utils.cache import Cacheable


class GNormPlus(Cacheable):
    """
    Helper class that accesses the rest API for GNormPlus from NCBI
    and returns a list of annotated genes for a given PMID
    """

    def __init__(self):
        super().__init__()
        self.url = 'http://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/RESTful/tmTool.cgi/Gene/{}/PubTator/'
        self.baseurl = "http://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/RESTful/tmTool.cgi/"
        self.regex = re.compile(r'[a-z]*:?(\d+).*', re.IGNORECASE)

    def get_genes_for_pmid(self, pmid, postproc=False):
        """
        For pmid get Genes in 4-tuple.
        If wanting to postprocess, meaning no 'GeneID:XXXX/...' then provide True boolean.
        :param pmid: PubMED ID
        :param postproc: postprocessing option for excluding 'GeneID:XXX...' to 'XXX'
        :return: (int, int, str, str)
        """
        if pmid in self.cache:
            text = self.cache[pmid]
        else:
            req = requests.get(self.url.format(pmid))
            text = req.text
            self.cache[pmid] = text

        genes = []
        for line in text.splitlines()[2:-1]:  # skip title and abstract
            try:
                _, start, end, text, _, gene_id = line.split('\t')
                if postproc:
                    gene_id = self.regex.sub(r'\1', gene_id)
                genes.append((int(start), int(end), text, gene_id))
            # the provided pmid was not a valid one
            except ValueError:
                pass
        return genes

    def get_genes_for_text(self, doc, docid='sampleid', postproc=False):
        """
        Retrieval via RESTful API with full documents.
        Attention!: one call can take a very long time. (no idea why, but sometimes it takes years and might not even finish)
        :param doc: Document that is supplied
        :type doc: nala.structures.data.Document
        :param postproc: postprocessing option for excluding 'GeneID:XXX...' to 'XXX'
        :return: list of GeneIDs in EntrezGene-Format (Number)
        """
        title = doc.get_title()
        if title in self.cache:
            # note considers if title as unique (no difference between full text and only abstract)
            text = self.cache[title]
        else:
            # submit
            data = docid + '|t|' + doc.get_title() + '\n' + docid + '|a|' + doc.get_body() + '\n'
            req = requests.post(self.baseurl + 'GNormPlus/Submit/', data=data)
            id = req.text

            # receive
            status = 'Not yet'  # todo test whether really working... because it s never finishing (all time 'Not yet')
            while status.startswith('Not yet'):
                req = requests.get(self.baseurl + id + '/Receive/')
                status = req.text
                time.sleep(5)

            # save in text and cache
            text = status
            # todo clean print statement
            print(text)
            self.cache[title] = text

        genes = []
        for line in text.splitlines()[2:-1]:  # skip title and abstract
            try:
                _, start, end, text, _, gene_id = line.split('\t')
                if postproc:
                    gene_id = self.regex.sub(r'\1', gene_id)
                genes.append((int(start), int(end), text, gene_id))
            # the provided pmid was not a valid one
            except ValueError:
                pass
        return genes

    def uniquify_genes(self, genes_object):
        """
        :param genes_object: (int, int, str, str)
        :return: unique list of genes in an array
        """
        return_list = []
        for gene in genes_object:
            return_list.append(gene[3])
        return_list = list(set(return_list))
        return return_list
