import sys
import logging
from pythonjsonlogger import jsonlogger
from scraperx import Scraper, run_cli, Dispatch, Download, Extract, run_task

# ## Basic logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(name)s - [%(scraper_name)s] %(message)s'
# )

# ## Or json logging (has a lot more data)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s',
                                     '%Y-%m-%dT%H:%M:%SZ')
s_handler = logging.StreamHandler(sys.stdout)
s_handler.setFormatter(formatter)
root_logger.addHandler(s_handler)


class TF2MapLinksDispatch(Dispatch):

    def submit_tasks(self):
        return {
            'url': 'https://tf2maps.net/downloads/categories/maps.2/?page=1',
            'page': 1,
        }


# This class is not actually needed, it will do the below action by default
#  leaving it here so you know it exists
class TF2MapLinksDownload(Download):

    def download(self):

        r = self.request_get(self.task['url'])
        self.save_request(r)


class TF2MapLinksExtract(Extract):

    def extract(self, raw_source, source_idx):

        yield self.extract_task(
            name='map_links',
            selectors=['li.resourceListItem'],
            callback=self.extract_map_links,
            # We do not need to actually save any data here
            # post_extract=self.save_as,
            # post_extract_kwargs={'file_format': 'json'},
        )
        yield self.extract_task(
            name='page',
            selectors=['div.PageNav nav a.text'],
            callback=self.extract_next_page
        )

    def extract_map_links(self, element, idx, **kwargs):
        map_href = element.css('h3.title a:last-of-type').xpath('@href').extract_first()
        task = {'url': f'https://tf2maps.net/{map_href}',
                'map_id': map_href.split('/')[1],
                }
        # Pass this new task to the scraper that will get the map details
        run_task(map_detail_scraper, task, task_cls=map_detail_scraper.download)

    def extract_next_page(self, element, idx, **kwargs):
        # No need to save any data, just here to trigger the next task
        # TODO: Will need to determine if you still need the next page based on what maps are still needed
        if self.task['page'] < 2:
            # Only get the first 2 pages to test
            next_page = element.xpath('@href').extract_first()
            # logger.info(f"Getting next page at {next_page}")
            new_task = {'url': f'https://tf2maps.net/{next_page}',
                        'page': self.task['page'] + 1,
                        }
            # Get the next page
            run_task(self.scraper, new_task, task_cls=self.scraper.download)


class TF2MapDetailsExtract(Extract):
    # No need for and Dispatch method here since it is getting passed tasks by the other scraper

    def extract(self, raw_source, source_idx):
        yield self.extract_task(
            name='map_details',
            selectors=[],
            callback=self.extract_map_details,
            post_extract=self.save_as,
            post_extract_kwargs={'file_format': 'json'},
        )

    def extract_map_details(self, element, idx, **kwargs):
        dl_url_href = element.css('label.downloadButton a').xpath('@href').extract_first()
        # TODO: download the files here
        return {'dl_url': f'https://tf2maps.net/{dl_url_href}',
                'map_id': self.task['map_id'],
                'map_name': element.css('div.resourceInfo h1::text').extract_first().strip(),
                'map_tagline': element.css('div.resourceInfo p.tagLine').xpath('string()').extract_first().strip(),
                'author_name': element.css('dl.author a').xpath('string()').extract_first().strip(),
                'author_id': element.css('dl.author a').xpath('@href').extract_first().split('/')[-2],
                'first_release_epoch': element.css('dl.firstRelease abbr').xpath('@data-time').extract_first(),
                'last_update_epoch': element.css('dl.lastUpdate abbr').xpath('@data-time').extract_first(),
                'category': element.css('dl.resourceCategory a').xpath('string()').extract_first().strip(),
                }


# Go to each page and find the links to the maps
map_links_scraper = Scraper(dispatch_cls=TF2MapLinksDispatch,
                            download_cls=TF2MapLinksDownload,
                            extract_cls=TF2MapLinksExtract,
                            scraper_name='tf2map_links')

# Get the details of the map by going to that page
map_detail_scraper = Scraper(extract_cls=TF2MapDetailsExtract,
                             scraper_name='tf2map_details')


if __name__ == '__main__':
    run_cli(map_links_scraper)
