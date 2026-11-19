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
            message: message.to_string(),
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

    /// Read up to `nbits` from the input, returns (bits_read, value)
    pub fn read(&mut self, nbits: u8) -> (u8, u8) {
        let mut value = 0u8;
        let mut count = 0u8;
        while count < nbits.min(8) {
            let Some(&byte) = self.input.get(self.byte_pos) else {
                break;
            };
            let bit = (byte >> (7 - self.bit_pos)) & 1;
            value = (value << 1) | bit;
            count += 1;
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

impl<'a> BitWriter<'a> {
    pub fn new(output: Option<&'a mut [u8]>, len: usize) -> Self {
        let count_only = output.is_none();
        Self {
            output,
            len,
            cur_bit: 0,
            count_only,
        }
    }

    /// Write `nbits` bits from `value` to the output
    /// Clears any unused low bits in the final byte written.
    /// Returns the number of bytes used so far or an error
    pub fn write(&mut self, nbits: u8, value: u8) -> Result<usize, Base122Error> {
        let nbits = usize::from(nbits.min(8));
        let end_bit = self.cur_bit + nbits;
        if let Some(out) = self.output.as_deref_mut() {
            let capacity = self.len.min(out.len()) * 8;
            if end_bit > capacity {
                return Err(Base122Error::new("Output does not have sufficient size"));
            }
            for i in 0..nbits {
                let bit = (value >> (nbits - 1 - i)) & 1;
                let pos = self.cur_bit + i;
                let mask = 0x80u8 >> (pos % 8);
                if bit == 1 {
                    out[pos / 8] |= mask;
                } else {
                    out[pos / 8] &= !mask;
                }
            }
            let bits_used = end_bit % 8;
            if nbits > 0 && bits_used != 0 {
                out[end_bit / 8] &= u8::MAX << (8 - bits_used);
            }
        }
        self.cur_bit = end_bit;
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
fn get_illegal_index(val: u8) -> Option<u8> {
    ILLEGALS
        .iter()
        .position(|&i| i == val)
        .and_then(|i| u8::try_from(i).ok())
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
    let mut size = 0;
    encode_internal(input, None, &mut size)?;
    let mut out = vec![0u8; size];
    let mut written = 0;
    encode_internal(input, Some(&mut out), &mut written)?;
    out.truncate(written);
    Ok(out)
}

/// Store one encoded byte (or only count it when there is no output buffer).
fn emit(
    output: &mut Option<&mut [u8]>,
    out_written: &mut usize,
    byte: u8,
) -> Result<(), Base122Error> {
    if let Some(out) = output.as_deref_mut() {
        let slot = out
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
    let mut reader = BitReader::new(input);
    *out_written = 0;
    loop {
        let (nbits, raw) = reader.read(7);
        if nbits == 0 {
            return Ok(());
        }
        // Align the first bit to position 6, e.g. 0abc0000.
        let bits = raw << (7 - nbits);
        if !is_illegal(bits) {
            emit(&mut output, out_written, bits)?;
            continue;
        }
        let illegal_index = get_illegal_index(bits).unwrap_or(0);
        let (next_nbits, next_raw) = reader.read(7);
        let (b1, next_bits) = if next_nbits == 0 {
            (0xC2 | (0x7 << 2), bits)
        } else {
            (0xC2 | (illegal_index << 2), next_raw << (7 - next_nbits))
        };
        emit(&mut output, out_written, b1 | ((next_bits >> 6) & 1))?;
        emit(&mut output, out_written, 0x80 | (next_bits & 0x3F))?;
    }
}

/// Write the last 7 bits of byteVal for decoding.
/// Returns an error if byteVal has 1 bits exceeding the last byte boundary.
fn write_last_7(writer: &mut BitWriter, byte_val: u8) -> Result<(), Base122Error> {
    // Do not write extra bytes. Write up to the nearest bit boundary.
    let nbits = 8 - (writer.cur_bit % 8) as u8;
    if nbits == 8 {
        return Err(Base122Error::new("Decoded data is not a byte multiple"));
    }
    // Any 1 bits after the last real bits are unexpected.
    let mask = !(0xFFu8 << (7 - nbits));
    if byte_val & mask != 0 {
        return Err(Base122Error::new(
            "Encoded data is malformed. Last byte has extra data.",
        ));
    }
    writer.write(nbits, byte_val >> (7 - nbits)).map(|_| ())
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
    let mut size = 0;
    decode_internal(input, &mut BitWriter::new(None, 0), &mut size)?;
    let mut out = vec![0u8; size];
    let len = out.len();
    let mut written = 0;
    decode_internal(input, &mut BitWriter::new(Some(&mut out), len), &mut written)?;
    out.truncate(written);
    Ok(out)
}

/// Write 7 bits, or only the trailing partial bits when `is_last` is set.
fn write_7(writer: &mut BitWriter, val: u8, is_last: bool) -> Result<(), Base122Error> {
    if is_last {
        write_last_7(writer, val)
    } else {
        writer.write(7, val & 0x7F).map(|_| ())
    }
}

/// Internal function to perform the decoding
fn decode_internal(
    input: &[u8],
    writer: &mut BitWriter,
    out_written: &mut usize,
) -> Result<(), Base122Error> {
    let mut pos = 0;
    while pos < input.len() {
        let cur = input[pos];
        pos += 1;
        if cur >> 7 == 0 {
            write_7(writer, cur, pos == input.len())?;
            continue;
        }
        // Expect first byte to have form 110xxx1y.
        if cur & 0xE2 != 0xC2 {
            return Err(Base122Error::new(
                "First byte of two byte sequence malformed",
            ));
        }
        let Some(&next) = input.get(pos) else {
            return Err(Base122Error::new(
                "Two byte sequence is missing second byte",
            ));
        };
        pos += 1;
        // Expect second byte to have form 10xxxxxx.
        if next & 0xC0 != 0x80 {
            return Err(Base122Error::new(
                "Second byte of two byte sequence malformed",
            ));
        }
        let is_last = pos == input.len();
        let trailing = ((cur & 1) << 6) | (next & 0x3F);
        match usize::from((cur & 0x1C) >> 2) {
            7 => {
                // Shortened two byte sequence.
                if !is_last {
                    return Err(Base122Error::new(
                        "Got unexpected extra data after shortened two byte sequence",
                    ));
                }
                write_7(writer, trailing, true)?;
            }
            idx if idx < ILLEGALS.len() => {
                writer.write(7, ILLEGALS[idx])?;
                write_7(writer, trailing, is_last)?;
            }
            _ => return Err(Base122Error::new("Got unrecognized illegal index")),
        }
    }
    *out_written = writer.cur_bit / 8;
    Ok(())
}
