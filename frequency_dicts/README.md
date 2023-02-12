wani freq py script how to use
pulled from: https://community.wanikani.com/t/frequency-generator-for-yomichan/47140

Basically you run the script in a directory with one folder called `books` that has all the books
(as long as calibre can read them and they are text not pictures any format works perhaps even PDFs might work)
and a folder called `dictionary` that holds all the dictionary
you have with yomichan(like jmdict). and run the script. the scrip assumes that you have

a python 3 interpreter  
calibre’s `ebook-convert`  
`jumanpp`  
zip (Copyright © 1990-2008 Info-ZIP - Type ‘zip “-L”’ for software license. This is Zip 3.0 (July 5th 2008), by Info-ZIP.)  
(optional) `tqdm`(python package) for progress bar

in the `PATH`. when you run the scripts it unpacks all dictionary and books and generate a frequency dictionary called freq named `freq.zip.`  
when you import it with yomichan, it will start showing the number of times a words occurred in the corpus.  
The first run is very slow, but it caches a lot of the intermediate formats and the subsequent runs are just slow.
