// The nested `card::card` path is part of the benchmark's public layout.
#[allow(clippy::module_inception)]
pub mod card {
    use std::sync::{Mutex, PoisonError};

    pub const CLUB_BITS: u32 = 4 << 5;
    pub const ACE_BITS: u32 = 1;
    pub const J_BITS: u32 = 11;
    pub const R8_BITS: u32 = 8;
    pub const R10_BITS: u32 = 10;
    pub const HEART_BITS: u32 = 2 << 5;
    pub const R4_BITS: u32 = 4;
    pub const SPADE_BITS: u32 = 1 << 5;
    pub const Q_BITS: u32 = 12;
    pub const R7_BITS: u32 = 7;
    pub const R5_BITS: u32 = 5;
    pub const K_BITS: u32 = 13;
    pub const R3_BITS: u32 = 3;
    pub const RANK_BITS: u32 = 0x1F;
    pub const R9_BITS: u32 = 9;
    pub const SUIT_BITS: u32 = 0x7 << 5;
    pub const R6_BITS: u32 = 6;
    pub const INVALID_CARD_BITS: u32 = 0;
    pub const DIAMOND_BITS: u32 = 3 << 5;
    pub const R2_BITS: u32 = 2;

    #[derive(Debug, Clone, Copy, PartialEq, PartialOrd)]
    pub enum CardSuitRank {
        SpadeAce, Spade2, Spade3, Spade4, Spade5, Spade6, Spade7, Spade8,
        Spade9, Spade10, SpadeJ, SpadeQ, SpadeK,
        HeartAce, Heart2, Heart3, Heart4, Heart5, Heart6, Heart7, Heart8,
        Heart9, Heart10, HeartJ, HeartQ, HeartK,
        DiamondAce, Diamond2, Diamond3, Diamond4, Diamond5, Diamond6,
        Diamond7, Diamond8, Diamond9, Diamond10, DiamondJ, DiamondQ, DiamondK,
        ClubAce, Club2, Club3, Club4, Club5, Club6, Club7, Club8, Club9,
        Club10, ClubJ, ClubQ, ClubK,
        CardCount,
        InvalidCard,
    }

    /// Suits in `CardSuitRank` order: the suit, its bits in a card byte and
    /// the letter used in string representations.
    const SUIT_TABLE: [(CardSuit, u32, char); 4] = [
        (CardSuit::Spade, SPADE_BITS, 'S'),
        (CardSuit::Heart, HEART_BITS, 'H'),
        (CardSuit::Diamond, DIAMOND_BITS, 'D'),
        (CardSuit::Club, CLUB_BITS, 'C'),
    ];

    /// Ranks in `CardRank` order (Ace first): the rank, its bits in a card byte
    /// and its label.
    const RANK_TABLE: [(CardRank, u32, &str); 13] = [
        (CardRank::Ace, ACE_BITS, "A"),
        (CardRank::R2, R2_BITS, "2"),
        (CardRank::R3, R3_BITS, "3"),
        (CardRank::R4, R4_BITS, "4"),
        (CardRank::R5, R5_BITS, "5"),
        (CardRank::R6, R6_BITS, "6"),
        (CardRank::R7, R7_BITS, "7"),
        (CardRank::R8, R8_BITS, "8"),
        (CardRank::R9, R9_BITS, "9"),
        (CardRank::R10, R10_BITS, "10"),
        (CardRank::J, J_BITS, "J"),
        (CardRank::Q, Q_BITS, "Q"),
        (CardRank::K, K_BITS, "K"),
    ];

    const RANKS_PER_SUIT: usize = RANK_TABLE.len();

    /// The 52 real cards in `CardSuitRank` order.
    const ALL_CARDS: [CardSuitRank; 52] = [
        CardSuitRank::SpadeAce, CardSuitRank::Spade2, CardSuitRank::Spade3,
        CardSuitRank::Spade4, CardSuitRank::Spade5, CardSuitRank::Spade6,
        CardSuitRank::Spade7, CardSuitRank::Spade8, CardSuitRank::Spade9,
        CardSuitRank::Spade10, CardSuitRank::SpadeJ, CardSuitRank::SpadeQ,
        CardSuitRank::SpadeK,
        CardSuitRank::HeartAce, CardSuitRank::Heart2, CardSuitRank::Heart3,
        CardSuitRank::Heart4, CardSuitRank::Heart5, CardSuitRank::Heart6,
        CardSuitRank::Heart7, CardSuitRank::Heart8, CardSuitRank::Heart9,
        CardSuitRank::Heart10, CardSuitRank::HeartJ, CardSuitRank::HeartQ,
        CardSuitRank::HeartK,
        CardSuitRank::DiamondAce, CardSuitRank::Diamond2, CardSuitRank::Diamond3,
        CardSuitRank::Diamond4, CardSuitRank::Diamond5, CardSuitRank::Diamond6,
        CardSuitRank::Diamond7, CardSuitRank::Diamond8, CardSuitRank::Diamond9,
        CardSuitRank::Diamond10, CardSuitRank::DiamondJ, CardSuitRank::DiamondQ,
        CardSuitRank::DiamondK,
        CardSuitRank::ClubAce, CardSuitRank::Club2, CardSuitRank::Club3,
        CardSuitRank::Club4, CardSuitRank::Club5, CardSuitRank::Club6,
        CardSuitRank::Club7, CardSuitRank::Club8, CardSuitRank::Club9,
        CardSuitRank::Club10, CardSuitRank::ClubJ, CardSuitRank::ClubQ,
        CardSuitRank::ClubK,
    ];

    impl CardSuitRank {
        /// Builds the card at the given suit and rank positions.
        fn from_parts(suit: usize, rank: usize) -> CardSuitRank {
            ALL_CARDS[suit * RANKS_PER_SUIT + rank]
        }

        /// Splits a real card into its (suit, rank) positions in the tables,
        /// or returns `None` for the two sentinel values.
        fn split(self) -> Option<(usize, usize)> {
            let index = self as usize;
            (index < ALL_CARDS.len()).then_some((index / RANKS_PER_SUIT, index % RANKS_PER_SUIT))
        }

        /// The byte pattern of this card, or `INVALID_CARD_BITS` for a sentinel.
        fn bits(self) -> u32 {
            match self.split() {
                Some((suit, rank)) => SUIT_TABLE[suit].1 | RANK_TABLE[rank].1,
                None => INVALID_CARD_BITS,
            }
        }

        pub fn cardtostr(&self) -> Option<String> {
            let (suit, rank) = self.split()?;
            Some(format!("{}{}", SUIT_TABLE[suit].2, RANK_TABLE[rank].2))
        }
    }

    #[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
    pub enum CardRank {
        Ace, R2, R3, R4, R5, R6, R7, R8, R9, R10, J, Q, K,
        RankCount,
        InvalidRank,
    }

    impl CardRank {
        pub fn ranktostr(&self) -> Option<String> {
            RANK_TABLE
                .iter()
                .find(|entry| entry.0 == *self)
                .map(|entry| String::from(entry.2))
        }

        pub fn strtorank(str: &str) -> CardRank {
            match str.as_bytes() {
                [digit @ b'2'..=b'9', ..] => RANK_TABLE[usize::from(digit - b'1')].0,
                [b'1', b'0', ..] => CardRank::R10,
                [first, ..] => match first.to_ascii_uppercase() {
                    b'A' => CardRank::Ace,
                    b'J' => CardRank::J,
                    b'Q' => CardRank::Q,
                    b'K' => CardRank::K,
                    _ => CardRank::InvalidRank,
                },
                [] => CardRank::InvalidRank,
            }
        }
    }

    #[derive(Debug, Clone, Copy, PartialEq, PartialOrd)]
    pub enum CardSuit {
        Spade, Heart, Diamond, Club,
        SuitCount,
        InvalidSuit,
    }

    /// A playing card, stored as a byte: the suit in the top three bits and
    /// the rank in the lower five bits.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    pub struct Card {
        card: u8
    }

    impl Card {
        /// Position of this card's suit in `SUIT_TABLE`.
        fn suit_index(&self) -> Option<usize> {
            let bits = u32::from(self.card) & SUIT_BITS;
            SUIT_TABLE.iter().position(|entry| entry.1 == bits)
        }

        /// Position of this card's rank in `RANK_TABLE`.
        fn rank_index(&self) -> Option<usize> {
            let bits = u32::from(self.card) & RANK_BITS;
            RANK_TABLE.iter().position(|entry| entry.1 == bits)
        }

        pub fn write_card(csr: CardSuitRank) -> Self {
            Card { card: csr.bits() as u8 }
        }

        pub fn get_card_suit_rank(&self) -> CardSuitRank {
            match (self.suit_index(), self.rank_index()) {
                (Some(suit), Some(rank)) => CardSuitRank::from_parts(suit, rank),
                _ => CardSuitRank::InvalidCard,
            }
        }

        pub fn get_card_rank(&self) -> CardRank {
            self.rank_index()
                .map_or(CardRank::InvalidRank, |rank| RANK_TABLE[rank].0)
        }

        pub fn get_card_suit(&self) -> CardSuit {
            self.suit_index()
                .map_or(CardSuit::InvalidSuit, |suit| SUIT_TABLE[suit].0)
        }

        pub fn create_card(csr: CardSuitRank) -> Option<Self> {
            csr.split().map(|_| Self::write_card(csr))
        }

        pub fn strtocard(str: &str) -> Option<Self> {
            let &[suit_byte, rank_byte] = str.as_bytes() else {
                return None;
            };
            let suit_letter = char::from(suit_byte.to_ascii_uppercase());
            let suit = SUIT_TABLE.iter().position(|entry| entry.2 == suit_letter)?;
            let rank_byte = rank_byte.to_ascii_uppercase();
            let rank = RANK_TABLE
                .iter()
                .position(|entry| entry.2.as_bytes() == [rank_byte])?;
            Self::create_card(CardSuitRank::from_parts(suit, rank))
        }
    }

    /// A node of a singly linked list of cards. A node whose `c` is `None` is a
    /// sentinel: it heads a collection and stands for the position before the
    /// first card and after the last card when a sorter is consulted.
    pub struct CardCollection {
        next: Option<Box<CardCollection>>,
        c: Option<Card>,
    }

    impl Drop for CardCollection {
        fn drop(&mut self) {
            // Unlink iteratively so that dropping a long chain cannot exhaust the stack.
            let mut next = self.next.take();
            while let Some(mut node) = next {
                next = node.next.take();
            }
        }
    }

    impl CardCollection {
        /// An empty collection: a sentinel with no successors.
        fn empty() -> Self {
            CardCollection { next: None, c: None }
        }

        /// Visits the cards after this sentinel in order.
        fn iter_cards(&self) -> impl Iterator<Item = Card> + '_ {
            std::iter::successors(self.next.as_deref(), |node| node.next.as_deref())
                .filter_map(|node| node.c)
        }

        /// Places `card` at the first position where `sorter` accepts it, trying
        /// the head, every gap between cards and the tail in that order.
        /// Returns whether a position was found.
        fn insert_sorted(&mut self, card: Card, sorter: CardSorter) -> bool {
            let new = Some(card);
            let mut cursor = self;
            loop {
                let before = cursor.c;
                let after = cursor.next.as_ref().and_then(|node| node.c);
                if sorter(&before, &new, &after) != 0 {
                    let rest = cursor.next.take();
                    cursor.next = Some(Box::new(CardCollection { next: rest, c: new }));
                    return true;
                }
                match cursor.next.as_deref_mut() {
                    Some(node) => cursor = node,
                    None => return false,
                }
            }
        }

        /// The card at 0-based `pos` (sentinel excluded), if there is one.
        fn card_at(&self, pos: usize) -> Option<Card> {
            self.iter_cards().nth(pos)
        }

        /// Removes the card at 0-based `pos` (sentinel excluded) and returns it.
        fn unlink_at(&mut self, pos: usize) -> Option<Card> {
            let mut link = &mut self.next;
            for _ in 0..pos {
                link = &mut link.as_mut()?.next;
            }
            let mut removed = link.take()?;
            *link = removed.next.take();
            removed.c
        }

        /// Inserts `c` at the position chosen by `sorter`; an absent card is ignored.
        pub fn insert_into_collection(mut self, c: Option<Card>, sorter: CardSorter) -> Self {
            if let Some(card) = c {
                self.insert_sorted(card, sorter);
            }
            self
        }

        /// Returns the entry after this one, or this entry itself when it is the last.
        pub fn iterate_collection(&self) -> &Self {
            self.next.as_deref().unwrap_or(self)
        }

        /// Appends `new` (with its own successors) after the last entry.
        pub fn append_into_collection(mut self, new: Self) -> Self {
            let mut link = &mut self.next;
            while let Some(node) = link {
                link = &mut node.next;
            }
            *link = Some(Box::new(new));
            self
        }

        /// Unlinks and drops the entry that `entry` refers to, matched by identity.
        /// Does nothing if `entry` is empty or is not part of this collection.
        pub fn detach_from_collection(&mut self, entry: &Option<Box<CardCollection>>) {
            let Some(target) = entry.as_deref() else {
                return;
            };
            let position = std::iter::successors(self.next.as_deref(), |node| node.next.as_deref())
                .position(|node| std::ptr::eq(node, target));
            if let Some(pos) = position {
                self.unlink_at(pos);
            }
        }
    }

    pub struct CardHand {
        max: u8,
        len: u8,
        sorter: CardSorter,
        cards: CardCollection,
    }

    impl CardHand {
        pub fn create_hand(max: u8, sorter: CardSorter) -> Option<CardHand> {
            Some(CardHand {
                max,
                len: 0,
                sorter,
                cards: CardCollection::empty(),
            })
        }

        pub fn reset_hand(&mut self) {
            self.len = 0;
            self.cards.next = None;
        }

        /// Inserts a card unless the hand is full or there is no card.
        pub fn insert_into_hand(&mut self, c: &Option<Card>) {
            if self.len >= self.max {
                return;
            }
            let Some(card) = *c else {
                return;
            };
            if self.cards.insert_sorted(card, self.sorter) {
                self.len += 1;
            }
        }

        pub fn count_cards_in_hand(&self) -> u64 {
            u64::from(self.len)
        }

        pub fn get_max_of_hand(&self) -> u64 {
            u64::from(self.max)
        }

        pub fn get_max_rank_of_hand(&self) -> CardRank {
            self.cards
                .iter_cards()
                .map(|card| card.get_card_rank())
                .max()
                .unwrap_or(CardRank::InvalidRank)
        }

        /// Visits the cards in order. `visit` receives the current length, the
        /// position and the card, and decides whether to continue, stop, or remove
        /// the card. A removed card is not counted in the position, so the next
        /// card takes the same position.
        fn walk<F>(&mut self, mut visit: F)
        where
            F: FnMut(u64, u64, &Option<Card>) -> ItrAction,
        {
            let mut pos = 0;
            while let Some(card) = self.cards.card_at(pos) {
                let len = u64::from(self.len);
                match visit(len, pos as u64, &Some(card)) {
                    ItrAction::Continue => pos += 1,
                    ItrAction::Break => break,
                    ItrAction::RemoveAndContinue => self.remove_at(pos),
                    ItrAction::RemoveAndBreak => {
                        self.remove_at(pos);
                        break;
                    }
                }
            }
        }

        /// Removes the card at `pos` from the hand.
        fn remove_at(&mut self, pos: usize) {
            if self.cards.unlink_at(pos).is_some() {
                self.len -= 1;
            }
        }

        pub fn iterate_hand(&mut self, itr_fn: CardIterator) {
            self.walk(itr_fn);
        }

        pub fn remove_from_hand(&mut self, c: CardSuitRank) {
            self.walk(|_, _, card| {
                if card.as_ref().is_some_and(|card| card.get_card_suit_rank() == c) {
                    ItrAction::RemoveAndContinue
                } else {
                    ItrAction::Continue
                }
            });
        }

        /// Removes the card at `pos`, which is the entry `CardCollection` refers to
        /// under an iteration.
        #[allow(non_snake_case)]
        pub fn remove_from_hand_under_iter(&mut self, CardCollection: &CardCollection, pos: usize) {
            let removed = self.cards.unlink_at(pos);
            debug_assert_eq!(removed, CardCollection.c);
            if removed.is_some() {
                self.len -= 1;
            }
        }
    }

    /// The cards still in the deck, in `CardSuitRank` order.
    pub struct CardDeck {
        cards: Vec<CardSuitRank>,
    }

    impl CardDeck {
        pub fn is_card_in_deck(&self, c: CardSuitRank) -> i32 {
            i32::from(self.cards.contains(&c))
        }

        /// Deals a card chosen by `lrand48() % remaining`, indexing the remaining
        /// cards in `CardSuitRank` order.
        pub fn deal_from_deck(&mut self) -> Option<Card> {
            if self.cards.is_empty() {
                return None;
            }
            let index = (lrand48() % self.cards.len() as u64) as usize;
            let csr = self.cards.remove(index);
            Card::create_card(csr)
        }

        pub fn strip_card_from_deck(&mut self, c: CardSuitRank) {
            self.cards.retain(|&card| card != c);
        }

        /// Creates a full deck. The order is not shuffled here: randomness is
        /// applied when cards are dealt.
        pub fn create_shuffled_deck() -> Option<CardDeck> {
            Some(CardDeck {
                cards: ALL_CARDS.to_vec(),
            })
        }
    }

    pub type CardSorter = fn(&Option<Card>, &Option<Card>, &Option<Card>) -> i32;

    /// Accepts a new card only at the end of the collection.
    pub fn sort_card_after(_before: &Option<Card>, _new: &Option<Card>, after: &Option<Card>) -> i32 {
        i32::from(after.is_none())
    }

    /// Accepts a new card after a lower rank and before a higher or equal rank.
    pub fn sort_card_by_rank(before: &Option<Card>, new: &Option<Card>, after: &Option<Card>) -> i32 {
        let Some(rank) = new.as_ref().map(Card::get_card_rank) else {
            return 0;
        };
        if after.is_none() {
            return 1;
        }
        let above_before = before.as_ref().is_none_or(|card| rank > card.get_card_rank());
        let below_after = after.as_ref().is_some_and(|card| rank <= card.get_card_rank());
        i32::from(above_before && below_after)
    }

    #[derive(Debug, Clone, Copy)]
    pub enum ItrAction {
        Continue,
        Break,
        RemoveAndContinue,
        RemoveAndBreak,
    }

    pub type CardIterator = fn(u64, u64, &Option<Card>) -> ItrAction;

    /// The POSIX 48-bit linear congruential generator behind `srand48`/`lrand48`.
    struct Lrand48 {
        state: u64,
    }

    impl Lrand48 {
        const MULTIPLIER: u64 = 0x5_DEEC_E66D;
        const INCREMENT: u64 = 0xB;
        const STATE_MASK: u64 = (1 << 48) - 1;
        const SEED_LOW_BITS: u64 = 0x330E;

        /// The state that `srand48(seed)` establishes.
        const fn seeded(seed: u32) -> Self {
            Lrand48 {
                state: ((seed as u64) << 16) | Self::SEED_LOW_BITS,
            }
        }

        /// Advances the state and returns its top 31 bits.
        fn next_31_bits(&mut self) -> u64 {
            self.state = self
                .state
                .wrapping_mul(Self::MULTIPLIER)
                .wrapping_add(Self::INCREMENT)
                & Self::STATE_MASK;
            self.state >> 17
        }
    }

    /// The single process-wide generator, as C's `lrand48` keeps one. It starts in
    /// the state of `srand48(3)`, the seed the benchmark's reference tests use.
    static LRAND48: Mutex<Lrand48> = Mutex::new(Lrand48::seeded(3));

    fn lrand48() -> u64 {
        let mut generator = LRAND48.lock().unwrap_or_else(PoisonError::into_inner);
        generator.next_31_bits()
    }
}
