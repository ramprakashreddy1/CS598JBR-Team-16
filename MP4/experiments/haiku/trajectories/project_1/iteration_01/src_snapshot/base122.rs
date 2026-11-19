//! Base122 encoder/decoder
//!
//! Base122 is a binary-to-text encoding scheme that avoids certain illegal characters
//! such as null, newline, carriage return, double quote, ampersand, and backslash.
use std::error::Error;
use std::fmt;

/// Error type for Base122 operations
#[derive(Debug, Clone)]
pub struct Base122Error {
    pub message: String,
}

impl Base122Error {
    fn new(message: &str) -> Self {
        Self {
            message: message.to_owned(),
        }
    }
}

impl fmt::Display for Base122Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.message)
    }
}

impl Error for Base122Error {}

/// BitReader is used to read bits from a byte array
pub struct BitReader<'a> {
    pub input: &'a [u8],
    pub byte_pos: usize,
    pub bit_pos: usize,
}

impl<'a> BitReader<'a> {
    pub fn new(input: &'a [u8]) -> Self {
        Self {
            input,
            byte_pos: 0,
            bit_pos: 0,
        }
    }

    /// Number of bits that have not been read yet.
    fn remaining_bits(&self) -> usize {
        (self.input.len() * 8).saturating_sub(self.byte_pos * 8 + self.bit_pos)
    }

    /// Read up to `nbits` from the input, returns (bits_read, value)
    ///
    /// `nbits` is capped at 8. The value is right-aligned; any unused high bits are zero.
    /// Returns `(0, 0)` once the input is exhausted.
    pub fn read(&mut self, nbits: u8) -> (u8, u8) {
        let count = nbits
            .min(8)
            .min(u8::try_from(self.remaining_bits()).unwrap_or(u8::MAX));
        let mut value = 0u8;
        for _ in 0..count {
            // `count` never exceeds the remaining bits, so this index is in range.
            let bit = (self.input[self.byte_pos] >> (7 - self.bit_pos)) & 1;
            value = (value << 1) | bit;
            self.bit_pos += 1;
            if self.bit_pos == 8 {
                self.bit_pos = 0;
                self.byte_pos += 1;
            }
        }
        (count, value)
    }
}

/// BitWriter is used to write bits to a byte array
pub struct BitWriter<'a> {
    pub output: Option<&'a mut [u8]>,
    pub len: usize,
    pub cur_bit: usize,
    pub count_only: bool,
}

const OUTPUT_TOO_SMALL: &str = "Output does not have sufficient size";

impl<'a> BitWriter<'a> {
    /// Creates a writer over `output`, or a counting-only writer when `output` is `None`.
    pub fn new(output: Option<&'a mut [u8]>, len: usize) -> Self {
        Self {
            count_only: output.is_none(),
            output,
            len,
            cur_bit: 0,
        }
    }

    /// Write `nbits` bits from `value` to the output
    /// Returns the number of bytes used so far or an error
    ///
    /// The low `nbits` bits of `value` are written most significant bit first.
    /// On error nothing is written. A counting-only writer only advances the bit position.
    pub fn write(&mut self, nbits: u8, value: u8) -> Result<usize, Base122Error> {
        let nbits = usize::from(nbits.min(8));
        let Some(output) = self.output.as_deref_mut().filter(|_| !self.count_only) else {
            self.cur_bit += nbits;
            return Ok(self.cur_bit.div_ceil(8));
        };
        if self.cur_bit + nbits > self.len * 8 {
            return Err(Base122Error::new(OUTPUT_TOO_SMALL));
        }
        for shift in (0..nbits).rev() {
            let bit = (value >> shift) & 1;
            let byte = output
                .get_mut(self.cur_bit / 8)
                .ok_or_else(|| Base122Error::new(OUTPUT_TOO_SMALL))?;
            let mask = 0x80u8 >> (self.cur_bit % 8);
            if bit == 1 {
                *byte |= mask;
            } else {
                *byte &= !mask;
            }
            self.cur_bit += 1;
        }
        Ok(self.cur_bit.div_ceil(8))
    }
}

const ILLEGALS: [u8; 6] = [
    0,  // null
    10, // newline
    13, // carriage return
    34, // double quote
    38, // ampersand
    92, // backslash
];

/// Check if a byte value is one of the illegal characters
fn is_illegal(val: u8) -> bool {
    ILLEGALS.contains(&val)
}

/// Get the index of an illegal character in the ILLEGALS array
fn get_illegal_index(val: u8) -> u8 {
    ILLEGALS
        .iter()
        .position(|&illegal| illegal == val)
        .and_then(|index| u8::try_from(index).ok())
        .unwrap_or(u8::MAX)
}

/// Encode binary data to Base122 encoding
///
/// # Arguments
///
/// * `input` - The binary data to encode
///
/// # Returns
///
/// * `Ok(Vec<u8>)` - The encoded data
/// * `Err(Base122Error)` - If there was an error during encoding
pub fn encode(input: &[u8]) -> Result<Vec<u8>, Base122Error> {
    // First pass sizes the output, second pass fills it.
    let mut len = 0;
    encode_internal(input, None, &mut len)?;

    let mut out = vec![0u8; len];
    let mut written = 0;
    encode_internal(input, Some(out.as_mut_slice()), &mut written)?;
    Ok(out)
}

/// Append one byte to the output, or only count it when there is no output buffer.
fn emit_byte(
    output: &mut Option<&mut [u8]>,
    out_written: &mut usize,
    byte: u8,
) -> Result<(), Base122Error> {
    if let Some(buf) = output.as_deref_mut() {
        let slot = buf
            .get_mut(*out_written)
            .ok_or_else(|| Base122Error::new("output does not have sufficient size"))?;
        *slot = byte;
    }
    *out_written += 1;
    Ok(())
}

/// Internal function to perform the encoding
fn encode_internal(
    input: &[u8],
    mut output: Option<&mut [u8]>,
    out_written: &mut usize,
) -> Result<(), Base122Error> {
    *out_written = 0;
    let mut reader = BitReader::new(input);

    loop {
        let (nbits, value) = reader.read(7);
        if nbits == 0 {
            break;
        }
        // Align the first bit to start at position 6, e.g. nbits = 3: 0abc0000.
        let bits = value << (7 - nbits);

        if is_illegal(bits) {
            // Two-byte sequence: 110xxx1y 10yyyyyy. Try to take the next 7 bits.
            let illegal_index = get_illegal_index(bits);
            let (next_nbits, next_value) = reader.read(7);
            let next_bits = next_value << (7 - next_nbits);

            let (b1, b2) = if next_nbits == 0 {
                // Shortened sequence: the illegal value itself is carried in the 7 payload bits.
                (0xC2 | (0x7 << 2) | ((bits >> 6) & 1), 0x80 | (bits & 0x3F))
            } else {
                (
                    0xC2 | (illegal_index << 2) | ((next_bits >> 6) & 1),
                    0x80 | (next_bits & 0x3F),
                )
            };
            emit_byte(&mut output, out_written, b1)?;
            emit_byte(&mut output, out_written, b2)?;
        } else {
            emit_byte(&mut output, out_written, bits)?;
        }
    }
    Ok(())
}

/// Write the last 7 bits of byte_val for decoding.
/// Returns an error if byte_val has 1 bits exceeding the last byte boundary.
fn write_last_7(writer: &mut BitWriter, byte_val: u8) -> Result<(), Base122Error> {
    // Only write up to the nearest bit boundary, so no extra bytes are produced.
    // `cur_bit % 8` is below 8, so the cast cannot truncate.
    let bit_offset = (writer.cur_bit % 8) as u8;
    if bit_offset == 0 {
        return Err(Base122Error::new("Decoded data is not a byte multiple"));
    }
    let nbits = 8 - bit_offset;
    // Example: nbits = 2, so the 5 low bits must be zero.
    let padding_bits = 7 - nbits;
    if byte_val & ((1u8 << padding_bits) - 1) != 0 {
        return Err(Base122Error::new(
            "Encoded data is malformed. Last byte has extra data.",
        ));
    }
    writer.write(nbits, byte_val >> padding_bits)?;
    Ok(())
}

/// Write one 7-bit payload, using the byte-boundary rules when it is the final payload.
fn write_payload(writer: &mut BitWriter, payload: u8, is_last: bool) -> Result<(), Base122Error> {
    if is_last {
        write_last_7(writer, payload)
    } else {
        writer.write(7, payload)?;
        Ok(())
    }
}

/// Decode Base122 encoded data to binary
///
/// # Arguments
///
/// * `input` - The Base122 encoded data
///
/// # Returns
///
/// * `Ok(Vec<u8>)` - The decoded binary data
/// * `Err(Base122Error)` - If there was an error during decoding
pub fn decode(input: &[u8]) -> Result<Vec<u8>, Base122Error> {
    // First pass validates the input and sizes the output, second pass fills it.
    let mut count_writer = BitWriter::new(None, 0);
    let mut len = 0;
    decode_internal(input, &mut count_writer, &mut len)?;

    let mut out = vec![0u8; len];
    let mut writer = BitWriter::new(Some(out.as_mut_slice()), len);
    let mut written = 0;
    decode_internal(input, &mut writer, &mut written)?;
    Ok(out)
}

/// Decode one two-byte sequence (`first` has already been consumed; `rest` holds the remaining input).
fn decode_two_byte_sequence(
    first: u8,
    rest: &mut &[u8],
    writer: &mut BitWriter,
) -> Result<(), Base122Error> {
    // Expect first byte to have form 110xxx1y.
    if (first & 0xE2) != 0xC2 {
        return Err(Base122Error::new(
            "First byte of two byte sequence malformed",
        ));
    }
    let current = *rest;
    let Some((&second, tail)) = current.split_first() else {
        return Err(Base122Error::new("Two byte sequence is missing second byte"));
    };
    *rest = tail;
    // Expect second byte to have form 10xxxxxx.
    if (second & 0xC0) != 0x80 {
        return Err(Base122Error::new(
            "Second byte of two byte sequence malformed",
        ));
    }

    let illegal_index = (first & 0x1C) >> 2;
    // The 7-bit payload: the y bit followed by the six low bits of the second byte.
    let payload = ((first & 0x01) << 6) | (second & 0x3F);
    match illegal_index {
        // Shortened two byte sequence: it must be the final unit of the input.
        7 => {
            if !rest.is_empty() {
                return Err(Base122Error::new(
                    "Got unexpected extra data after shortened two byte sequence",
                ));
            }
            write_payload(writer, payload, true)
        }
        index => {
            let illegal = ILLEGALS
                .get(usize::from(index))
                .ok_or_else(|| Base122Error::new("Got unrecognized illegal index"))?;
            writer.write(7, *illegal)?;
            write_payload(writer, payload, rest.is_empty())
        }
    }
}

/// Internal function to perform the decoding
fn decode_internal(
    input: &[u8],
    writer: &mut BitWriter,
    out_written: &mut usize,
) -> Result<(), Base122Error> {
    let mut rest = input;
    while let Some((&first, tail)) = rest.split_first() {
        rest = tail;
        if (first >> 7) == 0 {
            // One byte sequence.
            write_payload(writer, first, rest.is_empty())?;
        } else {
            decode_two_byte_sequence(first, &mut rest, writer)?;
        }
    }
    *out_written = writer.cur_bit / 8;
    Ok(())
}
