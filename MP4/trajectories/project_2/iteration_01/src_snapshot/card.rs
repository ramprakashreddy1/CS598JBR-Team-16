#[allow(clippy::module_inception)]
pub mod card {
    use std::sync::atomic::{AtomicU64, Ordering};

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

    /// Every real card, indexed by its `CardSuitRank` discriminant.
    const ALL_CARDS: [CardSuitRank; CardSuitRank::CardCount as usize] = [
        CardSuitRank::SpadeAce, CardSuitRank::Spade2, CardSuitRank::Spade3, CardSuitRank::Spade4,
        CardSuitRank::Spade5, CardSuitRank::Spade6, CardSuitRank::Spade7, CardSuitRank::Spade8,
        CardSuitRank::Spade9, CardSuitRank::Spade10, CardSuitRank::SpadeJ, CardSuitRank::SpadeQ,
        CardSuitRank::SpadeK,
        CardSuitRank::HeartAce, CardSuitRank::Heart2, CardSuitRank::Heart3, CardSuitRank::Heart4,
        CardSuitRank::Heart5, CardSuitRank::Heart6, CardSuitRank::Heart7, CardSuitRank::Heart8,
        CardSuitRank::Heart9, CardSuitRank::Heart10, CardSuitRank::HeartJ, CardSuitRank::HeartQ,
        CardSuitRank::HeartK,
        CardSuitRank::DiamondAce, CardSuitRank::Diamond2, CardSuitRank::Diamond3,
        CardSuitRank::Diamond4, CardSuitRank::Diamond5, CardSuitRank::Diamond6,
        CardSuitRank::Diamond7, CardSuitRank::Diamond8, CardSuitRank::Diamond9,
        CardSuitRank::Diamond10, CardSuitRank::DiamondJ, CardSuitRank::DiamondQ,
        CardSuitRank::DiamondK,
        CardSuitRank::ClubAce, CardSuitRank::Club2, CardSuitRank::Club3, CardSuitRank::Club4,
        CardSuitRank::Club5, CardSuitRank::Club6, CardSuitRank::Club7, CardSuitRank::Club8,
        CardSuitRank::Club9, CardSuitRank::Club10, CardSuitRank::ClubJ, CardSuitRank::ClubQ,
        CardSuitRank::ClubK,
    ];
    const ALL_RANKS: [CardRank; CardRank::RankCount as usize] = [
        CardRank::Ace, CardRank::R2, CardRank::R3, CardRank::R4, CardRank::R5, CardRank::R6,
        CardRank::R7, CardRank::R8, CardRank::R9, CardRank::R10, CardRank::J, CardRank::Q,
        CardRank::K,
    ];
    const SUIT_BITS_TABLE: [u32; CardSuit::SuitCount as usize] =
        [SPADE_BITS, HEART_BITS, DIAMOND_BITS, CLUB_BITS];
    const SUIT_LETTERS: [char; CardSuit::SuitCount as usize] = ['S', 'H', 'D', 'C'];
    const RANK_NAMES: [&str; CardRank::RankCount as usize] =
        ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"];
    const RANKS_PER_SUIT: usize = CardRank::RankCount as usize;

    /// State of the POSIX 48-bit linear congruential generator, initialised
    /// as by `srand48(3)` and shared by every deck in the process.
    static RNG_STATE: AtomicU64 = AtomicU64::new((3 << 16) | 0x330E);

    /// Advances the generator and returns its top 31 bits, like `lrand48`.
    fn lrand48() -> u64 {
        let step = |x: u64| x.wrapping_mul(0x5DEECE66D).wrapping_add(0xB) & ((1 << 48) - 1);
        let previous = RNG_STATE
            .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |x| Some(step(x)))
            .unwrap_or_else(|x| x);
        step(previous) >> 17
    }

    impl CardSuitRank {
        pub fn cardtostr(&self) ->  Option<String> {
            let idx = *self as usize;
            if idx >= ALL_CARDS.len() {
                return None;
            }
            Some(format!("{}{}", SUIT_LETTERS[idx / RANKS_PER_SUIT], RANK_NAMES[idx % RANKS_PER_SUIT]))
        }
    }
    #[derive(Debug, Clone, Copy, PartialEq, PartialOrd)]
    pub enum CardRank {
        Ace, R2, R3, R4, R5, R6, R7, R8, R9, R10, J, Q, K,
        RankCount,
        InvalidRank,
    }
    impl CardRank {
        pub fn ranktostr(&self) -> Option<String> {
            RANK_NAMES.get(*self as usize).map(|name| (*name).to_string())
        }
        pub fn strtorank(str: &str) -> CardRank {
            let mut chars = str.chars();
            match chars.next() {
                Some('1') if chars.next() == Some('0') => CardRank::R10,
                Some(c) => Self::from_char(c),
                None => CardRank::InvalidRank,
            }
        }
        /// Parses a single-character rank (`A`, `2`..`9`, `J`, `Q`, `K`).
        fn from_char(c: char) -> CardRank {
            match c.to_ascii_uppercase() {
                'A' => CardRank::Ace,
                '2'..='9' => ALL_RANKS[c as usize - '1' as usize],
                'J' => CardRank::J,
                'Q' => CardRank::Q,
                'K' => CardRank::K,
                _ => CardRank::InvalidRank,
            }
        }
    }
    #[derive(Debug, Clone, Copy, PartialEq, PartialOrd)]
    pub enum CardSuit {
        Spade, Heart, Diamond, Club,
        SuitCount,
        InvalidSuit,
    }
    #[derive(Debug, Clone, Copy, PartialEq)]
    pub struct Card {
        card: u8
    }
    impl Card {
        pub fn write_card(csr: CardSuitRank) -> Self {
            let idx = csr as usize;
            let bits = if idx < ALL_CARDS.len() {
                SUIT_BITS_TABLE[idx / RANKS_PER_SUIT] | (idx % RANKS_PER_SUIT + 1) as u32
            } else {
                INVALID_CARD_BITS
            };
            Card { card: bits as u8 }
        }
        pub fn get_card_suit_rank(&self) -> CardSuitRank {
            let suit = self.get_card_suit() as usize;
            let rank = self.get_card_rank() as usize;
            if suit >= CardSuit::SuitCount as usize || rank >= RANKS_PER_SUIT {
                return CardSuitRank::InvalidCard;
            }
            ALL_CARDS[suit * RANKS_PER_SUIT + rank]
        }
        pub fn get_card_rank(&self) -> CardRank {
            let rank = u32::from(self.card) & RANK_BITS;
            if (ACE_BITS..=K_BITS).contains(&rank) {
                ALL_RANKS[rank as usize - 1]
            } else {
                CardRank::InvalidRank
            }
        }
        pub fn get_card_suit(&self) -> CardSuit {
            match u32::from(self.card) & SUIT_BITS {
                SPADE_BITS => CardSuit::Spade,
                HEART_BITS => CardSuit::Heart,
                DIAMOND_BITS => CardSuit::Diamond,
                CLUB_BITS => CardSuit::Club,
                _ => CardSuit::InvalidSuit,
            }
        }
        pub fn create_card(csr: CardSuitRank) -> Option<Self> {
            Some(Self::write_card(csr)).filter(|c| u32::from(c.card) != INVALID_CARD_BITS)
        }
        pub fn strtocard(str: &str) -> Option<Self> {
            if str.len() != 2 {
                return None;
            }
            let mut chars = str.chars();
            let suit_letter = chars.next()?.to_ascii_uppercase();
            let suit = SUIT_LETTERS.iter().position(|&l| l == suit_letter)?;
            let rank = CardRank::from_char(chars.next()?);
            if rank == CardRank::InvalidRank {
                return None;
            }
            Self::create_card(ALL_CARDS[suit * RANKS_PER_SUIT + rank as usize])
        }
    }
    /// An ordered collection of cards.
    #[derive(Debug, Clone, Default)]
    pub struct CardCollection {
        cards: Vec<Card>,
    }
    impl CardCollection {
        pub fn insert_into_collection(mut self, c: Option<Card>, sorter: CardSorter) -> Self{
            let Some(card) = c else {
                return self;
            };
            let new = Some(card);
            let position = (0..=self.cards.len()).find(|&i| {
                let before = i.checked_sub(1).map(|b| self.cards[b]);
                sorter(&before, &new, &self.cards.get(i).copied()) != 0
            });
            match position {
                Some(i) => self.cards.insert(i, card),
                None if self.cards.is_empty() => self.cards.push(card),
                None => {}
            }
            self
        }
        pub fn iterate_collection(&self) -> &Self {
            self
        }
        pub fn append_into_collection(mut self, new: Self) -> Self {
            self.cards.extend(new.cards);
            self
        }
        pub fn detach_from_collection(&mut self, entry: &Option<Box<CardCollection>>) {
            if let Some(entry) = entry {
                for card in &entry.cards {
                    if let Some(i) = self.cards.iter().position(|c| c == card) {
                        self.cards.remove(i);
                    }
                }
            }
        }
    }
    pub struct CardHand {
        max: u8,
        sorter: CardSorter,
        cards: CardCollection,
    }
    impl CardHand {
        pub fn create_hand(max: u8, sorter: CardSorter) -> Option<CardHand> {
            Some(CardHand { max, sorter, cards: CardCollection::default() })
        }
        pub fn reset_hand(&mut self) {
            self.cards.cards.clear();
        }
        pub fn insert_into_hand(&mut self, c: &Option<Card>) {
            if self.cards.cards.len() >= usize::from(self.max) {
                return;
            }
            let cards = std::mem::take(&mut self.cards);
            self.cards = cards.insert_into_collection(*c, self.sorter);
        }
        pub fn count_cards_in_hand(&self) -> u64 {
            self.cards.cards.len() as u64
        }
        pub fn get_max_of_hand(&self) -> u64 {
            u64::from(self.max)
        }
        pub fn get_max_rank_of_hand(&self) -> CardRank {
            self.ranks()
                .reduce(|best, rank| if rank > best { rank } else { best })
                .unwrap_or(CardRank::InvalidRank)
        }
        /// The ranks of the cards in hand, in hand order.
        pub(crate) fn ranks(&self) -> impl Iterator<Item = CardRank> + '_ {
            self.cards.cards.iter().map(Card::get_card_rank)
        }
        pub fn iterate_hand(&mut self, itr_fn: CardIterator) {
            let mut pos = 0;
            while let Some(card) = self.cards.cards.get(pos).copied() {
                let len = self.cards.cards.len() as u64;
                match itr_fn(len, pos as u64, &Some(card)) {
                    ItrAction::Continue => pos += 1,
                    ItrAction::Break => break,
                    ItrAction::RemoveAndContinue => {
                        self.cards.cards.remove(pos);
                    }
                    ItrAction::RemoveAndBreak => {
                        self.cards.cards.remove(pos);
                        break;
                    }
                }
            }
        }
        pub fn remove_from_hand(&mut self, c: CardSuitRank) {
            self.cards.cards.retain(|card| card.get_card_suit_rank() != c);
        }
        /// Removes the card at `pos` of the hand while `_collection` (the
        /// collection being iterated) is traversed.
        pub fn remove_from_hand_under_iter (&mut self, _collection: &CardCollection, pos: usize) {
            if pos < self.cards.cards.len() {
                self.cards.cards.remove(pos);
            }
        }
    }
    pub struct CardDeck {
        card_count: u8,
        available: [bool; CardSuitRank::CardCount as usize],
    }
    impl CardDeck {
        pub fn is_card_in_deck(&self, c: CardSuitRank) -> i32 {
            i32::from(self.available.get(c as usize).copied().unwrap_or(false))
        }
        pub fn deal_from_deck(&mut self) -> Option<Card> {
            if self.card_count == 0 {
                return None;
            }
            let pick = (lrand48() % u64::from(self.card_count)) as usize;
            let idx = self
                .available
                .iter()
                .enumerate()
                .filter(|(_, &present)| present)
                .nth(pick)
                .map(|(i, _)| i)?;
            self.available[idx] = false;
            self.card_count -= 1;
            Some(Card::write_card(ALL_CARDS[idx]))
        }
        pub fn strip_card_from_deck(&mut self, c: CardSuitRank) {
            if let Some(present) = self.available.get_mut(c as usize) {
                if *present {
                    *present = false;
                    self.card_count -= 1;
                }
            }
        }
        pub fn create_shuffled_deck() -> Option<CardDeck> {
            Some(CardDeck {
                card_count: CardSuitRank::CardCount as u8,
                available: [true; CardSuitRank::CardCount as usize],
            })
        }
    }
    pub type CardSorter = fn(&Option<Card>, &Option<Card>, &Option<Card>) -> i32;
    pub fn sort_card_after(_before: &Option<Card>, _new: &Option<Card>, after: &Option<Card>) -> i32 {
        i32::from(after.is_none())
    }
    pub fn sort_card_by_rank(before: &Option<Card>, new: &Option<Card>, after: &Option<Card>) -> i32 {
        let rank = |c: &Option<Card>| c.as_ref().map(Card::get_card_rank);
        let fits = match (rank(new), rank(after)) {
            (_, None) => true,
            (Some(r), Some(after_rank)) => {
                rank(before).is_none_or(|before_rank| r > before_rank) && r <= after_rank
            }
            (None, Some(_)) => false,
        };
        i32::from(fits)
    }
    #[derive(Debug, Clone, Copy)]
    pub enum ItrAction {
        Continue,
        Break,
        RemoveAndContinue,
        RemoveAndBreak,
    }
    pub type CardIterator = fn(u64, u64, &Option<Card>) -> ItrAction;
}
