use crate::card::card::{Card, CardDeck, CardHand, CardRank};
// The nested `razz_simulation::razz_simulation` path is part of the benchmark's public layout.
#[allow(clippy::module_inception)]
pub mod razz_simulation {
    use super::*;
    use crate::card::card::{sort_card_by_rank, ItrAction};
    use std::cell::Cell;

    /// The number of cards each person is dealt in one round of Razz game.
    const RAZZ_CARD_IN_HAND_COUNT: u8 = 7;

    /// The number of distinct ranks that make a valid Razz hand.
    const RAZZ_RANKED_CARD_COUNT: u64 = 5;

    thread_local! {
        /// The rank of the card last kept while de-duplicating a hand.
        static PREVIOUS_RANK: Cell<Option<CardRank>> = const { Cell::new(None) };
    }

    pub struct DecidedCards {
        pub my_card_count: u8,
        pub my_cards: [Option<Card>; 3],
        pub opponent_card_count: u8,
        pub opponent_cards: [Option<Card>; 7],
    }

    pub type RankListener<T> = fn(&mut T, CardRank);

    pub fn simulate_razz_game<T>(decided_cards: &DecidedCards, game_count: u64, arg: &mut T, listener: RankListener<T>) -> i32 {
        let Some(mut my_hand) = CardHand::create_hand(RAZZ_CARD_IN_HAND_COUNT, sort_card_by_rank) else {
            eprintln!("Cannot create a hand");
            return 1;
        };

        for _ in 0..game_count {
            let Some(mut deck) = CardDeck::create_shuffled_deck() else {
                eprintln!("Cannot create a shuffled deck");
                return 1;
            };
            strip_deck(&mut deck, decided_cards);

            complete_hand(&mut my_hand, decided_cards, &mut deck);
            listener(arg, get_razz_rank(&mut my_hand));

            my_hand.reset_hand();
        }

        0
    }

    /// Removes the decided cards, which must not repeat, from the deck.
    pub fn strip_deck(deck: &mut CardDeck, decided_cards: &DecidedCards) {
        let my_cards = decided_cards
            .my_cards
            .iter()
            .take(usize::from(decided_cards.my_card_count));
        let opponent_cards = decided_cards
            .opponent_cards
            .iter()
            .take(usize::from(decided_cards.opponent_card_count));
        for card in my_cards.chain(opponent_cards).flatten() {
            deck.strip_card_from_deck(card.get_card_suit_rank());
        }
    }

    /// Fills my hand with the decided cards, then with cards dealt from the deck.
    pub fn complete_hand(my_hand: &mut CardHand, decided_cards: &DecidedCards, deck: &mut CardDeck) {
        let decided = usize::from(decided_cards.my_card_count);
        for card in decided_cards.my_cards.iter().take(decided) {
            my_hand.insert_into_hand(card);
        }

        let dealt = usize::from(RAZZ_CARD_IN_HAND_COUNT).saturating_sub(decided);
        for _ in 0..dealt {
            my_hand.insert_into_hand(&deck.deal_from_deck());
        }
    }

    /// Determines the Razz rank of a hand: the highest of its five lowest distinct
    /// ranks, or `InvalidRank` when it has fewer than five distinct ranks.
    fn get_razz_rank(hand: &mut CardHand) -> CardRank {
        hand.iterate_hand(remove_duplicated_rank);
        if hand.count_cards_in_hand() < RAZZ_RANKED_CARD_COUNT {
            return CardRank::InvalidRank;
        }

        hand.iterate_hand(keep_first_five);
        hand.get_max_rank_of_hand()
    }

    /// Removes every card whose rank repeats the rank of the card before it.
    fn remove_duplicated_rank(_len: u64, pos: u64, card: &Option<Card>) -> ItrAction {
        let Some(rank) = card.as_ref().map(Card::get_card_rank) else {
            return ItrAction::Continue;
        };
        PREVIOUS_RANK.with(|previous| {
            let is_duplicate = pos != 0 && previous.get() == Some(rank);
            if !is_duplicate {
                previous.set(Some(rank));
            }
            if is_duplicate {
                ItrAction::RemoveAndContinue
            } else {
                ItrAction::Continue
            }
        })
    }

    /// Removes every card from the fifth position onward.
    fn keep_first_five(_len: u64, pos: u64, _card: &Option<Card>) -> ItrAction {
        if pos >= RAZZ_RANKED_CARD_COUNT {
            ItrAction::RemoveAndContinue
        } else {
            ItrAction::Continue
        }
    }
}
