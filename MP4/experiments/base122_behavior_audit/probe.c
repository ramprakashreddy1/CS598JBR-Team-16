#include "base122.h"
#include <stdio.h>
#include <string.h>

int main(void) {
    char line[16390];
    unsigned char input[8192], output[16384];
    while (fgets(line, sizeof(line), stdin)) {
        size_t n = strcspn(line + 2, "\r\n") / 2;
        for (size_t i = 0; i < n; i++) {
            unsigned int byte;
            if (sscanf(line + 2 + 2*i, "%2x", &byte) != 1) return 2;
            input[i] = (unsigned char)byte;
        }
        size_t count = 0, written = 0;
        base122_error_t error = {0};
        int status;
        if (line[0] == 'e') {
            status = base122_encode(input, n, NULL, 0, &count, &error);
            if (!status) status = base122_encode(input, n, output, sizeof(output), &written, &error);
        } else {
            status = base122_decode(input, n, NULL, 0, &count, &error);
            if (!status) status = base122_decode(input, n, output, sizeof(output), &written, &error);
        }
        if (status) printf("err %s\n", error.msg);
        else {
            if (count != written) return 3;
            printf("ok ");
            for (size_t i = 0; i < written; i++) printf("%02x", output[i]);
            putchar('\n');
        }
    }
    return ferror(stdin) ? 4 : 0;
}
