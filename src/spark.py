from pyspark import SparkContext, SparkFiles, SparkConf
from WARCSplitReader import WARCSplitReader
from TextExtraction import TextExtraction
from EntityRecognition import EntityRecognition
from ELCandidateGeneration import ELCandidateGeneration
from OutputWriter import OutputWriter
from ELCandidateRanking import ELCandidateRanking
from ELMappingSelection import ELMappingSelection
import argparse

# Set Default Paramter for Entity Linking Pipeline
parser = argparse.ArgumentParser()
parser.add_argument("--es", help="Elastic Search instance.")
parser.add_argument("--kb", help="Trident instance.")
parser.add_argument("--f", help="Input file.")
parser.add_argument("--debug", help="Output some debug data.")
args = parser.parse_args()
es_path = "localhost:9200"
kb_path = "localhost:9090"
input_path = "sample.warc.gz"
debug = False
ranking_threshold = 0.5
model_root_path = "/var/scratch2/wdps1936/lib"
if args.es:
    es_path = args.es
if args.kb:
    kb_path = args.kb
if args.f:
    input_path = args.f

if args.debug == "True":
    debug = True
    model_root_path = "/data"

# Initialization Messages
print("Elastic Search Server:",es_path)
print("Trident Server:",kb_path)
print("Input file:", input_path)

conf = SparkConf().set("spark.ui.showConsoleProgress", "true")
sc = SparkContext(conf=conf)

print("STAGE 1 - Reading Input WARC")
input_file = sc.textFile(input_path)

wsr = WARCSplitReader(sc, input_file.collect())
wsr.parse_warc_records()
wsr.process_warc_records()
warc_stage_rdd = wsr.filter_invalid_records()
warc_stage_rdd.cache()
print("Processed: {0}".format(warc_stage_rdd.count()))

# Filter to intersting records:
if debug:
    recs=[
        "clueweb12-0000tw-00-00013"
    ]
    warc_stage_rdd = warc_stage_rdd.filter(lambda row: row["_id"] in recs)

print("STAGE 2 - Extracting Text")
text_prepro = TextExtraction(warc_stage_rdd)
text_prepro.clean_warc_responses()
text_prepro.extract_text_from_document()
txtprepro_stage_rdd = text_prepro.filter_unfit_records()
txtprepro_stage_rdd.cache()
print("Processed: {0}".format(txtprepro_stage_rdd.count()))

if debug:
    for row in txtprepro_stage_rdd.collect():
        print(row["sentences"])

# TODO: Currently Limiting: REMOVE LATER!
nlp_subset = txtprepro_stage_rdd.take(83)
txtprepro_stage_rdd = sc.parallelize(nlp_subset)

print("STAGE 3 - Entity Recognition incl. NLP-Preprocessing")
ee = EntityRecognition(txtprepro_stage_rdd)
ee_stage_rdd = ee.extract()
ee_stage_rdd.cache()
ee_stage_rdd = ee.join_sentences()
ee_stage_rdd.cache()
print("Processed: {0}".format(ee_stage_rdd.count()))

if debug:
    for row in ee_stage_rdd.collect():
        print(row)

print("STAGE 4 - Entity Linking - Candidate Generation")
el_cg = ELCandidateGeneration(ee_stage_rdd, es_path, ranking_threshold, model_root_path)
candidates_rdd = el_cg.get_candidates_from_elasticsearch()
candidates_rdd.cache()
print("Processed: {0}".format(candidates_rdd.count()))

print("STAGE 5 - Entity Linking - Candidate Ranking")
el_cr = ELCandidateRanking(candidates_rdd, kb_path, ranking_threshold, model_root_path)
el_cr.rank_entity_candidates()
el_cr.disambiguate_type()
ranked_candidates_rdd = el_cr.disambiguate_label()
ranked_candidates_rdd.cache()
print("Processed: {0}".format(ranked_candidates_rdd.count()))

print("STAGE 6 - Entity Linking - Mapping Selection")
el_ms = ELMappingSelection(ranked_candidates_rdd)
selected_entities_rdd = el_ms.select()
selected_entities_rdd.cache()
print("Processed: {0}".format(selected_entities_rdd.count()))

print("STAGE 7 - Writing Output")
ow = OutputWriter(selected_entities_rdd)
ow_stage_rdd = ow.convert_to_tsv()
ow_stage_rdd.cache()
print("Processed: {0}".format(ow_stage_rdd.count()))
ow_stage_rdd.saveAsTextFile("output/predictions.tsv")
