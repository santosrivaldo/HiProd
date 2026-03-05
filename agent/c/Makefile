# HiProd Agent C - Makefile (Linux / MinGW)
CC     ?= gcc
CFLAGS ?= -O2 -Wall -std=c11
CURL_CFLAGS := $(shell pkg-config --cflags libcurl 2>/dev/null || echo "-I/usr/include")
CURL_LIBS   := $(shell pkg-config --libs libcurl 2>/dev/null || echo "-lcurl")

SRCS = main.c config.c http.c api.c screen_capture.c windows_utils.c
OBJS = $(SRCS:.c=.o)
TARGET = hiprod_agent_c

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $(OBJS) $(CURL_LIBS)

%.o: %.c
	$(CC) $(CFLAGS) $(CURL_CFLAGS) -c -o $@ $<

clean:
	rm -f $(OBJS) $(TARGET) $(TARGET).exe
