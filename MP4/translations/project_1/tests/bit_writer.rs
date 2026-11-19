use libbase122::base122::BitWriter;

#[test]
fn clears_unused_bits_after_first_write() {
    let mut output = [0xff];
    let mut writer = BitWriter::new(Some(&mut output), 1);

    assert_eq!(writer.write(1, 0).unwrap(), 1);
    assert_eq!(writer.cur_bit, 1);
    assert_eq!(output, [0x00]);
}

#[test]
fn preserves_prefix_and_clears_suffix_in_mid_byte_write() {
    let mut output = [0x5a, 0xbf, 0x69];
    let mut writer = BitWriter::new(Some(&mut output), 3);
    writer.cur_bit = 11;

    assert_eq!(writer.write(2, 0xfd).unwrap(), 2);
    assert_eq!(writer.cur_bit, 13);
    assert_eq!(output, [0x5a, 0xa8, 0x69]);
}

#[test]
fn clears_unused_bits_after_crossing_byte_boundary() {
    let mut output = [0xbf, 0xff, 0x69];
    let mut writer = BitWriter::new(Some(&mut output), 3);
    writer.cur_bit = 3;

    assert_eq!(writer.write(6, 0xea).unwrap(), 2);
    assert_eq!(writer.cur_bit, 9);
    assert_eq!(output, [0xb5, 0x00, 0x69]);
}

#[test]
fn count_only_tracks_bytes_without_output_capacity() {
    let mut writer = BitWriter::new(None, 0);

    assert!(writer.count_only);
    assert_eq!(writer.write(7, 0xff).unwrap(), 1);
    assert_eq!(writer.write(2, 0xff).unwrap(), 2);
    assert_eq!(writer.cur_bit, 9);
    assert!(writer.output.is_none());
}

#[test]
fn insufficient_capacity_leaves_output_and_cursor_unchanged() {
    for (slice_len, len) in [(2, 1), (1, 2)] {
        let mut output = [0xbf, 0xff];
        let mut writer = BitWriter::new(Some(&mut output[..slice_len]), len);
        writer.cur_bit = 7;

        let error = writer.write(2, 0).unwrap_err();
        assert_eq!(error.message, "Output does not have sufficient size");
        assert_eq!(writer.cur_bit, 7);
        assert_eq!(output, [0xbf, 0xff]);
    }
}

#[test]
fn zero_bit_write_leaves_partial_byte_unchanged() {
    let mut output = [0xbf];
    let mut writer = BitWriter::new(Some(&mut output), 1);
    writer.cur_bit = 3;

    assert_eq!(writer.write(0, 0).unwrap(), 1);
    assert_eq!(writer.cur_bit, 3);
    assert_eq!(output, [0xbf]);
}
