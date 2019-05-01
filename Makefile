PYTHON := python  # assume it is python3
NUM_RQ_WORKER := 4

all:

rq-worker-start: 
	for i in {1..$(NUM_RQ_WORKER)}; do echo rq worker; done  | parallel --lb -j $(NUM_RQ_WORKER)

arxiv-db-populate:
	$(PYTHON) -m jrp.services.arxiv_feed populate 

pdf-db-update:
	$(PYTHON) -m jrp.services.pdf_main update_pdf_db --rq

pdf-db-update:
	$(PYTHON) -m jrp.services.pdf_main update_pdf_db --rq
