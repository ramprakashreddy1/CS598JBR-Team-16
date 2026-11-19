use razz_simulation::card::card::*;
use razz_simulation::razz_simulation::razz_simulation::*;
use std::sync::atomic::{AtomicUsize, Ordering};

const CARDS: [CardSuitRank; 52] = [
    CardSuitRank::SpadeAce, CardSuitRank::Spade2, CardSuitRank::Spade3, CardSuitRank::Spade4,
    CardSuitRank::Spade5, CardSuitRank::Spade6, CardSuitRank::Spade7, CardSuitRank::Spade8,
    CardSuitRank::Spade9, CardSuitRank::Spade10, CardSuitRank::SpadeJ, CardSuitRank::SpadeQ,
    CardSuitRank::SpadeK, CardSuitRank::HeartAce, CardSuitRank::Heart2, CardSuitRank::Heart3,
    CardSuitRank::Heart4, CardSuitRank::Heart5, CardSuitRank::Heart6, CardSuitRank::Heart7,
    CardSuitRank::Heart8, CardSuitRank::Heart9, CardSuitRank::Heart10, CardSuitRank::HeartJ,
    CardSuitRank::HeartQ, CardSuitRank::HeartK, CardSuitRank::DiamondAce, CardSuitRank::Diamond2,
    CardSuitRank::Diamond3, CardSuitRank::Diamond4, CardSuitRank::Diamond5, CardSuitRank::Diamond6,
    CardSuitRank::Diamond7, CardSuitRank::Diamond8, CardSuitRank::Diamond9, CardSuitRank::Diamond10,
    CardSuitRank::DiamondJ, CardSuitRank::DiamondQ, CardSuitRank::DiamondK, CardSuitRank::ClubAce,
    CardSuitRank::Club2, CardSuitRank::Club3, CardSuitRank::Club4, CardSuitRank::Club5,
    CardSuitRank::Club6, CardSuitRank::Club7, CardSuitRank::Club8, CardSuitRank::Club9,
    CardSuitRank::Club10, CardSuitRank::ClubJ, CardSuitRank::ClubQ, CardSuitRank::ClubK,
];
static MODE: AtomicUsize = AtomicUsize::new(0);

fn observe(len: u64, pos: u64, card: &Option<Card>) -> ItrAction {
    let id = card.as_ref().unwrap().get_card_suit_rank() as usize;
    println!("walk {len} {pos} {id}");
    match MODE.load(Ordering::Relaxed) {
        1 if pos == 2 => ItrAction::Break,
        2 if id % 3 == 0 => ItrAction::RemoveAndContinue,
        3 if id % 5 == 0 => ItrAction::RemoveAndBreak,
        _ => ItrAction::Continue,
    }
}

fn snapshot(hand: &mut CardHand) {
    let old = MODE.swap(0, Ordering::Relaxed);
    println!("hand {} {} {}", hand.count_cards_in_hand(), hand.get_max_of_hand(), hand.get_max_rank_of_hand() as usize);
    hand.iterate_hand(observe);
    MODE.store(old, Ordering::Relaxed);
}

fn listen(count: &mut u64, rank: CardRank) {
    println!("rank {count} {}", rank as usize);
    *count += 1;
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    match args[1].as_str() {
        "parse" => {
            for text in &args[2..] {
                let id = Card::strtocard(text).map(|c| c.get_card_suit_rank() as i32).unwrap_or(-1);
                println!("parse {} {id}", CardRank::strtorank(text) as usize);
            }
            for card in CARDS.into_iter().chain([CardSuitRank::CardCount, CardSuitRank::InvalidCard]) {
                let value = Card::create_card(card);
                println!("card {} {} {} {}", card as usize, card.cardtostr().unwrap_or_else(|| "-".into()),
                    value.as_ref().map(|c| c.get_card_rank() as i32).unwrap_or(-1),
                    value.as_ref().map(|c| c.get_card_suit() as i32).unwrap_or(-1));
            }
            let ranks = [CardRank::Ace,CardRank::R2,CardRank::R3,CardRank::R4,CardRank::R5,CardRank::R6,CardRank::R7,CardRank::R8,CardRank::R9,CardRank::R10,CardRank::J,CardRank::Q,CardRank::K,CardRank::RankCount,CardRank::InvalidRank];
            for rank in ranks { println!("name {} {}", rank as usize, rank.ranktostr().unwrap_or_else(|| "-".into())); }
        }
        "deck" => {
            seed_rng(args[2].parse::<i64>().unwrap() as u64);
            let scenario: usize = args[3].parse().unwrap();
            let mut a = CardDeck::create_shuffled_deck().unwrap();
            let mut b = CardDeck::create_shuffled_deck().unwrap();
            if scenario != 0 {
                for card in CARDS.into_iter().step_by(7) { a.strip_card_from_deck(card); a.strip_card_from_deck(card); }
            }
            for j in 0..55 {
                println!("deal {j} {}", a.deal_from_deck().map(|c| c.get_card_suit_rank() as i32).unwrap_or(-1));
                if scenario == 2 && j % 2 == 0 { println!("other {}", b.deal_from_deck().map(|c| c.get_card_suit_rank() as i32).unwrap_or(-1)); }
                for card in CARDS { print!("{}", i32::from(a.is_card_in_deck(card) != 0)); }
                println!();
            }
        }
        "hand" => {
            let cap = args[2].parse().unwrap();
            let sorter: usize = args[3].parse().unwrap();
            MODE.store(args[4].parse().unwrap(), Ordering::Relaxed);
            let mut hand = CardHand::create_hand(cap, if sorter == 0 { sort_card_after } else { sort_card_by_rank }).unwrap();
            for value in &args[5..] { hand.insert_into_hand(&Card::create_card(CARDS[value.parse::<usize>().unwrap()])); }
            snapshot(&mut hand);
            println!("callback");
            hand.iterate_hand(observe);
            snapshot(&mut hand);
            hand.remove_from_hand(CardSuitRank::SpadeAce);
            hand.remove_from_hand(CardSuitRank::HeartK);
            snapshot(&mut hand);
            hand.reset_hand();
            snapshot(&mut hand);
        }
        "simulate" => {
            seed_rng(args[2].parse::<i64>().unwrap() as u64);
            let scenario: usize = args[3].parse().unwrap();
            let rounds = args[4].parse().unwrap();
            let mut d = DecidedCards { my_card_count: 0, my_cards: [None;3], opponent_card_count: 0, opponent_cards: [None;7] };
            if scenario != 0 {
                d.my_card_count = (scenario % 4) as u8;
                d.opponent_card_count = (scenario % 8) as u8;
                for i in 0..usize::from(d.my_card_count) { d.my_cards[i] = Card::create_card(CARDS[i*13]); }
                for i in 0..usize::from(d.opponent_card_count) { d.opponent_cards[i] = Card::create_card(CARDS[3+i*3]); }
            }
            let mut count = 0;
            let status = simulate_razz_game(&d, rounds, &mut count, listen);
            println!("done {status} {count}");
        }
        _ => panic!("unknown audit operation"),
    }
}
