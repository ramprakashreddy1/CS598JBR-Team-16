use std::io::{self, BufRead};
use libbase122::base122::{decode, encode};

fn main() {
    for line in io::stdin().lock().lines() {
        let line = line.expect("probe input");
        let input: Vec<u8> = line.as_bytes()[2..].chunks_exact(2)
            .map(|pair| u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap())
            .collect();
        let result = if line.starts_with('e') { encode(&input) } else { decode(&input) };
        match result {
            Ok(output) => {
                if line.starts_with('e') {
                    assert_eq!(decode(&output).expect("encoded output must decode"), input);
                }
                print!("ok ");
                for byte in output { print!("{byte:02x}"); }
                println!();
            }
            Err(error) => println!("err {}", error.message),
        }
    }
}
