use crate::card::card::{sort_card_by_rank, Card, CardDeck, CardHand, CardRank};
#[allow(clippy::module_inception)]
pub mod razz_simulation {
    use super::*;
    /// The number of cards each person is dealt in one round of Razz game.
    const RAZZ_CARD_IN_HAND_COUNT: u8 = 7;
    /// The number of cards that make up a ranked Razz hand.
    const RAZZ_RANKED_CARD_COUNT: usize = 5;

    pub struct DecidedCards {
        pub my_card_count: u8,
        pub my_cards: [Option<Card>; 3],
        pub opponent_card_count: u8,
        pub opponent_cards: [Option<Card>; 7],
    }
    pub type RankListener<T> = fn(&mut T, CardRank);

    /// Determines the Razz rank of a hand: the highest of its five lowest
    /// distinct ranks, or `InvalidRank` if fewer than five distinct ranks exist.
    fn get_razz_rank(hand: &CardHand) -> CardRank {
        let mut distinct: Vec<CardRank> = hand.ranks().collect();
        distinct.dedup();
        distinct
            .get(RAZZ_RANKED_CARD_COUNT - 1)
            .copied()
            .unwrap_or(CardRank::InvalidRank)
    }

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
            listener(arg, get_razz_rank(&my_hand));
            my_hand.reset_hand();
        }
        0
    }
    pub fn strip_deck(deck: &mut CardDeck, decided_cards: &DecidedCards) {
        let mine = decided_cards.my_cards.iter().take(usize::from(decided_cards.my_card_count));
        let theirs = decided_cards
            .opponent_cards
            .iter()
            .take(usize::from(decided_cards.opponent_card_count));
        for card in mine.chain(theirs).flatten() {
            deck.strip_card_from_deck(card.get_card_suit_rank());
        }
    }
    pub fn complete_hand(my_hand: &mut CardHand, decided_cards: &DecidedCards, deck: &mut CardDeck) {
        let decided = usize::from(decided_cards.my_card_count).min(decided_cards.my_cards.len());
        for card in &decided_cards.my_cards[..decided] {
            my_hand.insert_into_hand(card);
        }
        for _ in decided..usize::from(RAZZ_CARD_IN_HAND_COUNT) {
            my_hand.insert_into_hand(&deck.deal_from_deck());
        }
    }
}
