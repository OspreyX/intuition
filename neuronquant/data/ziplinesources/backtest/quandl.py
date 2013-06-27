
#
# Copyright 2013 Quantopian, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tools to generate data sources.
"""
import pandas as pd

from zipline.gens.utils import hash_args
from zipline.sources.data_source import DataSource

from neuronquant.data.datafeed import DataFeed


class QuandlSource(DataSource):
    """
    Yields all events in event_list that match the given sid_filter.
    If no event_list is specified, generates an internal stream of events
    to filter.  Returns all events if filter is None.

    Configuration options:

    sids   : list of values representing simulated internal sids
    start  : start date
    delta  : timedelta between internal events
    filter : filter to remove the sids
    """

    def __init__(self, data_descriptor, **kwargs):
        assert isinstance(data_descriptor['index'], pd.tseries.index.DatetimeIndex)

        self.data_descriptor = data_descriptor
        # Unpack config dictionary with default values.
        self.sids  = kwargs.get('sids', data_descriptor['tickers'])
        self.start = kwargs.get('start', data_descriptor['index'][0])
        self.end   = kwargs.get('end', data_descriptor['index'][-1])

        # Hash_value for downstream sorting.
        self.arg_string = hash_args(data_descriptor, **kwargs)

        self._raw_data = None

        self.feed = DataFeed()

    @property
    def mapping(self):
        mapping = {
            'dt': (lambda x: x, 'dt'),
            'sid': (lambda x: x, 'sid'),
            'price': (float, 'Adjusted Close'),
            'volume': (int, 'Volume'),
        }

        # Add additional fields.
        for field_name in self.data:
            if field_name in ['Adjusted Close', 'Volume', 'dt', 'sid']:
                continue
            mapping[field_name] = (lambda x: x, field_name)

        return mapping

    @property
    def instance_hash(self):
        return self.arg_string

    def _get(self):
        #TODO Test here for one value, make it later a panel
        assert len(self.sids) == 1
        # Try to set quandl api key, stored in default config file
        self.feed._search_quandlkey()

        return self.feed.fetch_quandl(self.sids[0],
            start_date=self.start,
            end_date=self.end,
            returns='pandas')

    def raw_data_gen(self):
        self.data = self._get()
        sid = self.sids[0]
        for dt, series in self.data.iterrows():
            event = {
                'dt': dt,
                'sid': sid,
            }
            for field_name, value in series.iteritems():
                event[field_name] = value

            yield event

    @property
    def raw_data(self):
        if not self._raw_data:
            self._raw_data = self.raw_data_gen()
        return self._raw_data
