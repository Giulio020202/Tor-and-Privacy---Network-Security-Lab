CAPTURE_DIR=onion-net/captures

.PHONY: clean merge-captures
clean:
	rm -rf $(CAPTURE_DIR)

merge-captures:
	./onion-net/merge_pcaps.sh
