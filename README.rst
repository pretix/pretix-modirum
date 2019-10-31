Modirum payments for pretix
===========================

This is a plugin for `pretix`_. 

Development setup
-----------------

1. Make sure that you have a working `pretix development setup`_.

2. Clone this repository, eg to ``local/pretix-modirum``.

3. Activate the virtual environment you use for pretix development.

4. Execute ``python setup.py develop`` within this directory to register this application with pretix's plugin registry.

5. Execute ``make`` within this directory to compile translations.

6. Restart your local pretix server. You can now use the plugin from this repository for your events by enabling it in
   the 'plugins' tab in the settings.

Test card numbers
-----------------
==========  =======================  ===============  ====  ================  ============  ======  ==============
Card Type   Card Number              Expiration Date  CVV2  Card Holder Name  3D Secure     Result  3D Secure code
==========  =======================  ===============  ====  ================  ============  ======  ==============
Visa        4012 0000 0001 2003 001  12/2020          123   test              Challenge     ✔️       Secret33!
Visa        4012 0000 0001 2011 004  12/2020          123   test              Frictionless  ✔️
Visa        4012 0000 0001 2011 012  12/2020          123   test              Frictionless  ✖️
Visa        4012 0000 0001 2011 020  12/2020          123   test              Frictionless  U
Amex        3707 551000 0002         12/2020          123   test              Frictionless  ✔
MasterCard  5900 0700 0000 0003      12/2020          123   test              Frictionless  ✔
MasterCard  5900 0700 0000 0029      12/2020          123   test              Frictionless  ✖️
==========  =======================  ===============  ====  ================  ============  ======  ==============


License
-------


Copyright 2019 Raphael Michel

Released under the terms of the Apache License 2.0



.. _pretix: https://github.com/pretix/pretix
.. _pretix development setup: https://docs.pretix.eu/en/latest/development/setup.html
