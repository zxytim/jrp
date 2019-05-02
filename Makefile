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

pdf-db-update:
	$(PYTHON) -m jrp.services.pdf_main update_pdf_db --rq

arxiv-db-update:
	$(PYTHON) -m jrp.services.arxiv_feed update

arxiv-db-populate:
	$(PYTHON) -m jrp.services.arxiv_feed populate 

viz-service:
	$(PYTHON) -m jrp.services.viz_serve

prod-run-impl: thumbnail-db-update text-db-update pdf-db-update arxiv-db-update rq-worker-start

prod-run:
	$(MAKE) -j 10 prod-run-impl

# DEBUG
rq-dashboard:
	rq-dashboard
