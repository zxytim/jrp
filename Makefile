PYTHON := python  # assume it is python3

# starter plan on scaperapi
NUM_RQ_WORKER_IO := 30
NUM_RQ_WORKER_COMPUTATION := 10

all:

rq-worker-start: 
	$(PYTHON) -m jrp.services.rq_worker io:$(NUM_RQ_WORKER_IO) computation:$(NUM_RQ_WORKER_COMPUTATION)

thumbnail-db-update:
	$(PYTHON) -m jrp.services.pdf_main update_pdf_thumbnail_db --rq 

thumbnail-db-update-daemon:
	while true; do make thumbnail-db-update; sleep 60; done 

text-db-update:
	$(PYTHON) -m jrp.services.pdf_main update_pdf_text_db --rq 

text-db-update-daemon:
	while true; do make text-db-update; sleep 60; done 

pdf-db-update:
	$(PYTHON) -m jrp.services.pdf_main update_pdf_db --rq

pdf-db-update-daemon:
	while true; do make pdf-db-update; sleep 60; done 

arxiv-db-update:
	$(PYTHON) -m jrp.services.arxiv_feed update

arxiv-db-update-daemon:
	while true; do make pdf-db-update; sleep 3600; done 

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
