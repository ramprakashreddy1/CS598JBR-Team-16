#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "card.c"
#include "razz_simulation.c"

static int callback_mode;

static enum itr_action observe(unsigned long len, unsigned long pos, const card *c) {
  int id = get_card_suit_rank(c);
  printf("walk %lu %lu %d\n", len, pos, id);
  if (callback_mode == 1 && pos == 2) return BREAK;
  if (callback_mode == 2 && id % 3 == 0) return REMOVE_AND_CONTINUE;
  if (callback_mode == 3 && id % 5 == 0) return REMOVE_AND_BREAK;
  return CONTINUE;
}

static void snapshot(card_hand *h) {
  int saved_mode = callback_mode;
  callback_mode = 0;
  printf("hand %lu %lu %d\n", count_cards_in_hand(h), get_max_of_hand(h), get_max_rank_of_hand(h));
  iterate_hand(h, observe);
  callback_mode = saved_mode;
}

static void listen(void *arg, enum card_rank rank) {
  unsigned long *count = arg;
  printf("rank %lu %d\n", *count, rank);
  ++*count;
}

int main(int argc, char **argv) {
  if (argc < 2) return 2;
  if (!strcmp(argv[1], "parse")) {
    for (int i = 2; i < argc; ++i) {
      const card *c = strtocard(argv[i]);
      printf("parse %d %d\n", strtorank(argv[i]), c ? (int)get_card_suit_rank(c) : -1);
      if (c) destroy_card(&c);
    }
    for (int id = 0; id <= INVALID_CARD; ++id) {
      const card *c = create_card(id);
      const char *name = cardtostr(id);
      printf("card %d %s %d %d\n", id, name ? name : "-", c ? (int)get_card_rank(c) : -1, c ? (int)get_card_suit(c) : -1);
      if (c) destroy_card(&c);
    }
    for (int rank = 0; rank <= INVALID_RANK; ++rank) {
      const char *name = ranktostr(rank);
      printf("name %d %s\n", rank, name ? name : "-");
    }
    return 0;
  }
  if (!strcmp(argv[1], "deck")) {
    srand48(strtoll(argv[2], NULL, 10));
    int scenario = atoi(argv[3]);
    card_deck *a = create_shuffled_deck();
    card_deck *b = create_shuffled_deck();
    if (scenario) {
      for (int j = 0; j < 52; j += 7) {
        strip_card_from_deck(j, a);
        strip_card_from_deck(j, a);
      }
    }
    for (int j = 0; j < 55; ++j) {
      const card *c = deal_from_deck(a);
      printf("deal %d %d\n", j, c ? (int)get_card_suit_rank(c) : -1);
      if (scenario == 2 && j % 2 == 0) {
        const card *other = deal_from_deck(b);
        printf("other %d\n", other ? (int)get_card_suit_rank(other) : -1);
      }
      for (int k = 0; k < 52; ++k) printf("%d", is_card_in_deck(k, a) != 0);
      putchar('\n');
    }
    destroy_deck(&a);
    destroy_deck(&b);
    return 0;
  }
  if (!strcmp(argv[1], "hand")) {
    int cap = atoi(argv[2]), sorter = atoi(argv[3]);
    callback_mode = atoi(argv[4]);
    card_hand *h = create_hand(cap, sorter ? sort_card_by_rank : sort_card_after);
    for (int i = 5; i < argc; ++i) {
      const card *c = create_card(atoi(argv[i]));
      insert_into_hand(h, c);
    }
    snapshot(h);
    puts("callback");
    iterate_hand(h, observe);
    snapshot(h);
    remove_from_hand(h, SPADE_ACE);
    remove_from_hand(h, HEART_K);
    snapshot(h);
    reset_hand(h);
    snapshot(h);
    destroy_hand(&h);
    return 0;
  }
  if (!strcmp(argv[1], "simulate")) {
    srand48(strtoll(argv[2], NULL, 10));
    int scenario = atoi(argv[3]);
    unsigned long rounds = strtoul(argv[4], NULL, 10), count = 0;
    struct decided_cards d = {0};
    if (scenario) {
      d.my_card_count = scenario % 4;
      d.opponent_card_count = scenario % 8;
      for (int i = 0; i < d.my_card_count; ++i) d.my_cards[i] = create_card(i * 13);
      for (int i = 0; i < d.opponent_card_count; ++i) d.opponent_cards[i] = create_card(3 + i * 3);
    }
    int status = simulate_razz_game(&d, rounds, &count, listen);
    printf("done %d %lu\n", status, count);
    return 0;
  }
  return 2;
}
