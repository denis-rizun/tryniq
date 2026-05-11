.PHONY: build run clean

build:
	swift build -c release

run:
	swift run -c release streamer

clean:
	swift package clean
	rm -rf .build
