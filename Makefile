PYTHON := python  # assume it is python3

# starter plan on scaperapi
NUM_RQ_WORKER := 10

all:

rq-worker-start: 
	for i in {1..$(NUM_RQ_WORKER)}; do echo rq worker; done  | parallel --lb -j $(NUM_RQ_WORKER)

thumbnail-db-update:
	$(PYTHON) -m jrp.services.pdf_main update_pdf_thumbnail_db --rq 

text-db-update:
	$(PYTHON) -m jrp.services.pdf_main update_pdf_text_db --rq 

arxiv-db-populate:
	$(PYTHON) -m jrp.services.arxiv_feed populate 

pdf-db-update:
	$(PYTHON) -m jrp.services.pdf_main update_pdf_db --rq

pdf-db-update:
	$(PYTHON) -m jrp.services.pdf_main update_pdf_db --rq

