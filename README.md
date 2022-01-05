Selenium-based web scraper for Badoo dating service, that grabs person's interests.

Before scraping you provide scores for each interest, so you can sum up scores for each interest and find best matches (persons with biggest score).

Here is examples of scraped profiles:

![Profiles](/res/profile-data.png)

Here is result of select "find\_favorites.sql":

![Favorites](/res/favorites.png)

I've done it long ago, so it's probably won't work because they change markdown pretty often.

And also -- I've removed DB from commit, because I don't want to leak someont's personal data. If you want to get it for personal use -- do it yourself :)

If you want to use it, you will need to:

* Install Selenium and Gecko driver (if you use Firefox)
* Fix element ids, so they are up to date with the site
