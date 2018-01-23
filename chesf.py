# Copyright 2017 Domenico Delle Side <nico@delleside.org>
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing,
#    software distributed under the License is distributed on an "AS
#    IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#    express or implied.  See the License for the specific language
#    governing permissions and limitations under the License.

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import *
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from queue import PriorityQueue


MAX_ATTEMPTS = 3


class CHeSF(object):
    def __init__(self, driver_path='', window_size='1378x768', debug=False):
        """The constructor accepts for the moment the driver_path and the
        window_size.

        In the future we'll add further options.

        """
        self.__current_url = ''
        self._url_counter  = 0
        self._debug        = debug
        # in the future, we should check if the path exists, otherwise
        # raise an exception
        self.__driver_path = driver_path 

        # these options are somewhat fixed for the moment. In the
        # future will be passed through **kwargs
        self.__chrome_options = Options()
        
        if not debug:
            self.__chrome_options.add_argument('--disable-logging')
            self.__chrome_options.add_argument('--log-level=3')
            self.__chrome_options.add_argument('--silent')
            
        self.__chrome_options.add_argument('--disable-gpu')
        self.__chrome_options.add_argument('--lang=en-US')
        self.__chrome_options.add_argument('--headless')
        self.__chrome_options.add_argument('--window-size='+window_size)

        self.__webdriver = webdriver.Chrome(chrome_options=self.__chrome_options,
                                            executable_path=self.__driver_path)

        
        self._request_callbacks = {'before': None, 'after': None}
        self.__queue = PriorityQueue()
        Element.chesf  = self


    def __get_elements(self, method, selector, timeout):
        """A private method to conveniently wrap a call to find some
        element of a webpage.

        It accepts as arguments a method (currently 'css' or 'xpath')
        and a selector. In its logic, it implements some checks to
        prevent access to unexisting elements.

        The method returns a list of Element instances.

        """
        attempts = 0
        ret_elements = [] 
        by = ''

        if method == 'css':
            by = By.CSS_SELECTOR
        elif method == 'xpath':
            by = By.XPATH
        
        while attempts < MAX_ATTEMPTS:
            try:
                elements = WebDriverWait(self.__webdriver, timeout).until(
                    EC.visibility_of_all_elements_located((by, selector))
                )
                attempts = MAX_ATTEMPTS
                ret_elements = [Element(e, selector, method) for e in elements]
            except:
                attempts += 1
                if self._debug:
                    print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> %s <<' %(selector))

        return ret_elements


    def __wait_before_click(self, element, timeout=1):
        attempts = 0

        if element.selector_type == 'css':
            by = By.CSS_SELECTOR
        elif element.selector_type == 'xpath':
            by = By.XPATH
        
        while attempts < MAX_ATTEMPTS:
            try:
                WebDriverWait(self.__webdriver, timeout).until(
                    EC.element_to_be_clickable((by, element.selector))
                )
                attempts = MAX_ATTEMPTS
            except:
                attempts += 1
                if self._debug:
                    print('Unable to find a clickable element with selector "%s"' %(selector))

    
    def __enqueue(self, priority, data):
        """This private method is used to populate the priority queue
        consumed by the scraper. It accepts two arguments:

        - a _priority_, i.e. an integer greater or equal to zero a;
        - data dictionary, i.e. a data structure used by the scraper
          to perform specific actions.

        The lowest the value of _priority_, the sooner the associated
        actions are executed.

        Currently, the sole 0 priority action defined is the click on
        a given Element instance. Clicks, generally, are performed
        first because they are needed, for example, for
        paginations. Priority "1" actions are simple get of urls.

        The method does not return any explicit value.

        """
        
        if priority == 0:
            queue_element = (0, 0, data)
        else:
            queue_element = (1, self._url_counter, data)
        
        self.__queue.put_nowait(queue_element)


    def enqueue_click(self, element, cb):
        """This is a convenience method that wraps a call to self.__enqueue,
        taking care of all the necessary data.

        It accepts two arguments:

        - an Element object in element, representing the element to be
          clicked;
        - cb represents a callback function to parse the resulting document.

        The method does not return any explicit value.
        """
        
        data = {'url': '', 'element': element, 'callback': cb}
        self.__enqueue(0, data)
        if self._debug:
            print(">>>>>>>>> Enqueued element: %s" %(element))

        
    def enqueue_url(self, url, cb):
        """This is a convenience method that wraps a call to self.__enqueue,
        taking care of all the necessary data.

        It accepts two arguments:

        - an url representing a page to be parsed;
        - cb represents a callback function to parse the resulting document.

        The method does not return any explicit value.
        """
        
        data = {'url': url, 'element': '', 'callback': cb}
        self._url_counter += 1
        self.__enqueue(1, data)
        if self._debug:
            print("Enqueued url: %s (%i)" %(url, self._url_counter))

        
    def register_callback(self, when, cb):
        if when != 'before' and when != 'after':
            print('Not a valid callback event')
            exit(False)

        self._request_callbacks[when] = cb

        
    def call_js(self, js_code):
        """Although simple, this method is extremely powerful. It takes a
        single argument, representing the javascript code to be
        executed.

        Its return value is determined by the return value of the
        javascript code. So, you could use it to perform
        straightforward parsing in javascript, returning the parsed
        values directly to the python code. For example, consider a
        javascript code that returns the href attribute of all the "a"
        tags matching a given css class. You could store all the
        attributes in a javascript array and then return it. The
        values in the array will be directly available in the python
        code as a list. That's easy!

        This strategy is extremely useful to avoid any
        StaleElementReferenceException, very common when using
        selenium.

        """
        return self.__webdriver.execute_script(js_code)

        
    def quit(self):
        """
        Quit the browser and close the chrome driver.
        """
        self.__webdriver.quit()

        
    def parse(self):
        """This method is specific to the task the user want to perform. It
        has to be implemented in the user class.

        """

        message = """%s parse callback is not defined. You should implement it
        for a correct use of the framework 
        """
        
        raise NotImplementedError(message %(self.__class__.__name__))


    def current_url(self):
        """ This methods returns the last requested url as a string
        """
        return self.__current_url

    
    def start(self, start_url):
        """This is the core of the class. This method takes as input a start
        url, that it will analyze through the "parse" method (you
        should implement it, remember!)

        The url and the "parse" callback are added as the first
        element of task queue. You should add any further url or click
        (for paginations) to this queue in order to continue parsing
        other web pages. To the purpose, the methods "enqueue_url" and
        "enqueue_click" are provided.

        Clicks (which are generally used for paginations) have higher
        priority with respect to urls, and they are executed whenever
        one is inserted in the queue.

        You could define further callbacks, other than parse.

        """
        self.enqueue_url(start_url, self.parse)

        while (not self.__queue.empty()):
            # current_item is a list with 3 elements
            # - 0 is the main priority number (0 or 1)
            # - 1 is the secondary priority number (>= 0)
            # - 2 is the data
            current_item = self.__queue.get_nowait()

            if current_item is None:
                break

            if self._request_callbacks['before']:
                self._request_callbacks['before']()

            if current_item[0] == 0:
                self.__wait_before_click(current_item[2]['element'], timeout=0.5)
                if self._debug:
                    print("--------------------------> clicking a link")
                current_item[2]['element'].click()
            else:
                if self._debug:
                    print("++++++++++++++++++++++++++> getting an url")
                    print(current_item[2]['url'])
                self.__current_url = current_item[2]['url']
                self.__webdriver.get(current_item[2]['url'])

            if self._request_callbacks['after']:
                self._request_callbacks['after']()

            current_item[2]['callback']()
    
            
    def xpath(self, selector, timeout=5):
        """ Returns an array of Element instances matching the given Xpath selector """
        return self.__get_elements('xpath', selector, timeout)
    

    def css(self, selector, timeout=5):
        """ Returns an array of Element instances matching the given CSS selector """
        return self.__get_elements('css', selector, timeout)



class Element(object):
    chesf = None
    
    def __init__(self, webelement, selector=None, selector_type=None):
        self.__webelement = webelement
        self.selector = selector
        self.selector_type = selector_type
        

    def __str__(self):
        return 'Element obtained with (%s) selector: %s' %(self.selector_type, self.selector)

    
    def __repr__(self):
        return self.__str__()
    
        
    def attribute(self, name):
        return self.__webelement.get_attribute(name)

    
    def text(self):
        return self.__webelement.text

    
    def tag(self):
        return self.__webelement.tag_name

    
    def click(self):
        attempts = 0

        while attempts < MAX_ATTEMPTS:
            try: 
                self.__webelement.click()
                attempts = MAX_ATTEMPTS
            except StaleElementReferenceException:
                self.refresh()
                attempts += 1
                if Element.chesf._debug:
                    print('Element refreshed!')
            except WebDriverException:
                attempts += 0.1
                if Element.chesf._debug:
                    print('Element not clickable!')
                

        
    def is_displayed(self):
        return self.__webelement.is_displayed()


    def refresh(self):
        tmp = None
        attempts = 0

        while attempts < MAX_ATTEMPTS:
            if self.selector_type == 'css':
                tmp = Element.chesf.css(self.selector, 1)
            elif self.selector_type == 'xpath':
                tmp = Element.chesf.xpath(self.selector, 1)

            if len(tmp) > 0:
                # setting __webelement to tmp[0] could probably break in some
                # cases. A better implementation is needed
                self.__webelement = tmp[0]
                attempts = MAX_ATTEMPTS
            else:
                attempts += 1


