venv:
	python3 -m venv venv
	venv/bin/pip install -r requirements.txt

client:
	docker build -f delivery/client.Dockerfile -t suhoy/vg_client .

# pay attention to .ONESHELL and '@' in @docker
# https://www.gnu.org/software/make/manual/make.html#One-Shell
# https://stackoverflow.com/questions/3477292/what-do-and-do-as-prefixes-to-recipe-lines-in-make
.ONESHELL:
run_client:
	@docker rm vg_client
	docker run --name vg_client \
		--network verbose-goggles_main \
		--mount "type=bind,src=$(shell pwd)/tmp,dst=/app/tmp" \
		-it suhoy/vg_client
