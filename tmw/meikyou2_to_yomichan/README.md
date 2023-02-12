For meikyou_to_yomi:

I've already spent too much time on this, so I think I'll call it finished now. Here's the Python script. You can use this to create your very own copy of `明鏡国語辞典　第二版` for Yomichan. If you don't know how to use this or do not want to run an untrusted program on your computer, then I suggest you ask a trusted friend to do it for you. I am not distributing any material to which I do not possess copyright ownership. The script itself is very legal and very cool. Feel free to reupload the script and these instructions somewhere else, because I will be deleting these posts soon.

In order to run the script, you will first need to process your epwing copy of `明鏡国語辞典　第二版` using FooSoft's zero-epwing.

https://github.com/FooSoft/zero-epwing/releases

```
./zero-epwing -e -p -m Meikyou2/ > meikyou2.json
```

`Meikyou2/` should be a folder containing the appropriate CATALOGS file. Then run the Python script on this JSON file.

```
python meikyou2_to_yomichan.py meikyou2.json
```

The script will take about a minute to run and will produce a file named [Monolingual] 明鏡国語辞典　第二版.zip that you can import into Yomichan. No, the program isn't slow because I didn't compile the regex patterns. It's slow because it's using BeautifulSoup to parse the markup of 60k+ entries.

(script: https://cdn.discordapp.com/attachments/778430038159655012/998720522768625684/meikyou2_to_yomichan.py)

A couple things to note:

1. Furigana text is, by default, styled with a small font size and a subscript alignment. This font size is absolute; if you scale the size of your Yomichan popup using the "Scale" setting in your Yomichan options, then these furigana texts will not scale in size along with the rest of the text. This is because Yomichan only allows absolute font sizes in dictionary styles. There's no reason why it can't support relative font sizes ("smaller", "70%", etc.); this is just an oversight on the developer's part.

https://github.com/FooSoft/yomichan/blob/289a61a62fd5cb41223ef639b1e83e290e1a9c77/ext/data/schemas/dictionary-term-bank-v3-schema.json#L255

Anyway, you can adjust the font size and positioning yourself by adding some custom CSS to your Yomichan settings.

```
[data-sc-meikyo="furigana"] {
  font-size: 70% !important;
  vertical-align: sub !important;
}
```

2. The sense definitions are numbered using enclosed numbers like ①, ②, ③, etc. Unicode only goes up to ㊿, so after that they become Ⓐ, Ⓑ, Ⓒ, etc. There aren't many entries that have this many senses, so it's not a big deal.

Sometimes meikyo makes reference to senses from within other senses. For example, definition ④ might make a reference to definition ③. These references have been underlined in order to help you distinguish the references from the definition indices
