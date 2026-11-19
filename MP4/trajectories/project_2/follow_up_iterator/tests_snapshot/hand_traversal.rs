use razz_simulation::card::card::*;
use std::cell::RefCell;

type Visit = (u64, u64, CardSuitRank);
thread_local! {
    static VISITS: RefCell<Vec<Visit>> = const { RefCell::new(Vec::new()) };
}

fn observe(len: u64, pos: u64, card: &Option<Card>) -> ItrAction {
    VISITS.with(|v| v.borrow_mut().push((len, pos, card.unwrap().get_card_suit_rank())));
    ItrAction::Continue
}

fn take_visits() -> Vec<Visit> {
    VISITS.with(|v| std::mem::take(&mut *v.borrow_mut()))
}

fn hand(cards: &[CardSuitRank], sorter: CardSorter) -> CardHand {
    let mut hand = CardHand::create_hand(cards.len().try_into().unwrap(), sorter).unwrap();
    for &card in cards {
        hand.insert_into_hand(&Card::create_card(card));
    }
    hand
}

fn snapshot(hand: &mut CardHand) -> Vec<CardSuitRank> {
    take_visits();
    hand.iterate_hand(observe);
    let visits = take_visits();
    assert_eq!(visits.len() as u64, hand.count_cards_in_hand());
    for (pos, &(len, actual_pos, _)) in visits.iter().enumerate() {
        assert_eq!(len, hand.count_cards_in_hand());
        assert_eq!(actual_pos, pos as u64);
    }
    visits.into_iter().map(|(_, _, card)| card).collect()
}

fn remove_divisible_by_three(len: u64, pos: u64, card: &Option<Card>) -> ItrAction {
    observe(len, pos, card);
    if card.unwrap().get_card_suit_rank() as usize % 3 == 0 {
        ItrAction::RemoveAndContinue
    } else {
        ItrAction::Continue
    }
}

#[test]
fn removing_head_ends_this_traversal() {
    use CardSuitRank::*;
    let mut h = hand(&[SpadeAce, Spade4, Spade7], sort_card_after);
    h.iterate_hand(remove_divisible_by_three);
    assert_eq!(take_visits(), vec![(3, 0, SpadeAce)]);
    assert_eq!(snapshot(&mut h), vec![Spade4, Spade7]);
}

#[test]
fn duplicate_head_removal_stops_after_first_match() {
    use CardSuitRank::*;
    let mut h = hand(&[SpadeAce, SpadeAce, Spade2], sort_card_after);
    h.remove_from_hand(SpadeAce);
    assert_eq!(snapshot(&mut h), vec![SpadeAce, Spade2]);
    h.remove_from_hand(SpadeAce);
    assert_eq!(snapshot(&mut h), vec![Spade2]);
}

#[test]
fn all_actions_at_head_middle_and_tail() {
    use CardSuitRank::*;
    let cards = [Spade2, HeartAce, Diamond4];
    // Function pointers keep this exercise on the original public callback API.
    let callbacks: [CardIterator; 4] = [
        observe,
        |len, pos, c| { observe(len, pos, c); ItrAction::Break },
        |len, pos, c| { observe(len, pos, c); ItrAction::RemoveAndContinue },
        |len, pos, c| { observe(len, pos, c); ItrAction::RemoveAndBreak },
    ];
    // Rotate each action into each position using three distinct callbacks.
    thread_local! {
        static PLAN: RefCell<(usize, CardIterator)> = RefCell::new((0, observe));
    }
    fn planned(len: u64, pos: u64, c: &Option<Card>) -> ItrAction {
        PLAN.with(|p| {
            let (target, callback) = *p.borrow();
            if c.unwrap().get_card_suit_rank() == [Spade2, HeartAce, Diamond4][target] {
                callback(len, pos, c)
            } else {
                observe(len, pos, c)
            }
        })
    }
    for (action, callback) in callbacks.into_iter().enumerate() {
        for target in 0..cards.len() {
            PLAN.with(|p| *p.borrow_mut() = (target, callback));
            let mut h = hand(&cards, sort_card_after);
            h.iterate_hand(planned);
            let removes = action >= 2;
            let stops = action == 1 || action == 3 || (removes && target == 0);
            let visited = if stops { target + 1 } else { cards.len() };
            let expected: Vec<_> = cards.iter().take(visited).enumerate().map(|(i, &c)| {
                let shifted = removes && i > target;
                (3 - u64::from(shifted), i as u64 - u64::from(shifted), c)
            }).collect();
            assert_eq!(take_visits(), expected, "action {action}, target {target}");
            let mut remaining = cards.to_vec();
            if removes { remaining.remove(target); }
            assert_eq!(snapshot(&mut h), remaining);
        }
    }
}

#[test]
fn repeated_non_head_removals_keep_position_and_update_length() {
    use CardSuitRank::*;
    let mut h = hand(&[Spade2, Spade4, Spade7, Spade3], sort_card_after);
    h.iterate_hand(remove_divisible_by_three);
    assert_eq!(take_visits(), vec![(4, 0, Spade2), (4, 1, Spade4), (3, 1, Spade7), (2, 1, Spade3)]);
    assert_eq!(snapshot(&mut h), vec![Spade2, Spade3]);
}

#[test]
fn duplicate_non_head_matches_are_all_removed_including_tail() {
    use CardSuitRank::*;
    let mut h = hand(&[Spade2, SpadeAce, SpadeAce, Spade3, SpadeAce], sort_card_after);
    h.remove_from_hand(SpadeAce);
    assert_eq!(snapshot(&mut h), vec![Spade2, Spade3]);
    h.remove_from_hand(HeartK);
    assert_eq!(snapshot(&mut h), vec![Spade2, Spade3]);
}

#[test]
fn sorted_duplicate_ranks_and_cards_preserve_c_order() {
    use CardSuitRank::*;
    let mut h = hand(&[Spade2, SpadeAce, HeartAce, SpadeAce, Heart2], sort_card_by_rank);
    assert_eq!(snapshot(&mut h), vec![SpadeAce, HeartAce, SpadeAce, Heart2, Spade2]);
    h.remove_from_hand(SpadeAce);
    assert_eq!(snapshot(&mut h), vec![HeartAce, SpadeAce, Heart2, Spade2]);
    h.remove_from_hand(SpadeAce);
    assert_eq!(snapshot(&mut h), vec![HeartAce, Heart2, Spade2]);
}

#[test]
fn empty_and_singleton_hands_support_all_actions_and_reuse() {
    for action in [ItrAction::Continue, ItrAction::Break, ItrAction::RemoveAndContinue, ItrAction::RemoveAndBreak] {
        thread_local! { static ACTION: RefCell<ItrAction> = const { RefCell::new(ItrAction::Continue) }; }
        fn callback(len: u64, pos: u64, c: &Option<Card>) -> ItrAction {
            observe(len, pos, c);
            ACTION.with(|a| *a.borrow())
        }
        ACTION.with(|a| *a.borrow_mut() = action);
        let mut h = CardHand::create_hand(1, sort_card_after).unwrap();
        h.iterate_hand(callback);
        h.remove_from_hand(CardSuitRank::SpadeAce);
        assert!(take_visits().is_empty());
        h.insert_into_hand(&Card::create_card(CardSuitRank::SpadeAce));
        h.iterate_hand(callback);
        assert_eq!(take_visits(), vec![(1, 0, CardSuitRank::SpadeAce)]);
        assert_eq!(h.count_cards_in_hand(), u64::from(matches!(action, ItrAction::Continue | ItrAction::Break)));
        h.reset_hand();
        h.insert_into_hand(&Card::create_card(CardSuitRank::HeartK));
        assert_eq!(snapshot(&mut h), vec![CardSuitRank::HeartK]);
    }
}

#[test]
fn named_removal_handles_each_position_and_reinsertion() {
    use CardSuitRank::*;
    let cards = [Spade2, HeartAce, Diamond4];
    for target in 0..cards.len() {
        let mut h = hand(&cards, sort_card_after);
        h.remove_from_hand(cards[target]);
        let mut expected = cards.to_vec();
        expected.remove(target);
        assert_eq!(snapshot(&mut h), expected);
        h.insert_into_hand(&Card::create_card(ClubK));
        expected.push(ClubK);
        assert_eq!(snapshot(&mut h), expected);
        assert_eq!(h.get_max_rank_of_hand(), CardRank::K);
        assert_eq!(h.get_max_of_hand(), 3);
    }
}
