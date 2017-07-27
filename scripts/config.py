""" EBAY CONFIG
"""
def init_options():
   # Trading API - https://www.x.com/developers/ebay/products/trading-api
    compatability= '967'
    appid= '#'
    certid= '#'
    devid= '#'
    token= 'hwNcTIAnjr9EgiSb5HRjXvDZLFuQCFC7MePiOpTlgaXbpWfqV+djgVcC8QE6P3MMj1Sd2c6rKBmHrdx46G4bkh80cSQrBjRhJ6LzTQp2ls1LhgFXbZ7O9B6yWhkyCIP1WtrGGB0f+xwL/a/XQb2Dm4NlGLlAC7VliQC/6YSXT9cY5h4wPJQp7KxLnv9pQozT+4UxeYYbJHF8J2YWXzPXybiEE0+XIkbuj9n5fMeu52gGD/pvqw/Ps6Tm/twwHYW7zNHBWFSVSOMC06BqFUbVgnDp2X5xFL8nJtMrz4tgd/SvyVgGP3u+Crk4hl0jwYs7YWFM6ebVhjj6fcy3zYHMzacjbzv0P8vNQgTad3lka05FMz8II09dv1wVNxC4eJWIA9crMecNRH7nU1QKJMehrsETz9V3g3HDcg6j3L69skeSkl4R/6egXbvY8qIgTD+x+GfowIoIRHHjemHtzI5j+NajJBuSJCTvKqvLoykaZwAC+drKNuqdjBEPrzKRqgjEYLa4oPigOmIYxWdc2BFUJQRbze95GhxG+QBwaSt2GHkWWmWQQgcFC4LycKJAXLoOgseIqHmASTU5murp5T2V8BjbwSNeGzG90kQOxUNjIiP4BDsU4b78LtvdkbbJDx8AZ5oKPsUunUIYmZ8zLNByWM6xdrB3Ith+A8T'
   # token isn't valid =P
    return appid, certid, devid, token

#
# if __name__ == "__main__":
#     (opts, args) = init_options()

eBayConfig = {
  "name": "ebay_api_config",
  "api.sandbox.ebay.com": {
    "compatability": 967,
    "appid": "#",
    "certid": "#",
    "devid": "#",
    "token": "#2PrBmdj6wVnY+sEZ2PrA2dj6wHkoahAJaBqQudj6x9nY+seQ**0icDAA**AAMAAA**396dRmMG91ia1sJRg4j+bmG6jjSM7CTymxH3pj43BkRBarw8yxUKdgH9FdYC64Kf5oSH2pAiaOP3W+npn641h+duoK72chwNcTIAnjr9EgiSb5HRjXvDZLFuQCFC7MePiOpTlgaXbpWfqV+djgVcC8QE6P3MMj1Sd2c6rKBmHrdx46G4bkh80cSQrBjRhJ6LzTQp2ls1LhgFXbZ7O9B6yWhkyCIP1WtrGGB0f+xwL/a/XQb2Dm4NlGLlAC7VliQC/6YSXT9cY5h4wPJQp7KxLnv9pQozT+4UxeYYbJHF8J2YWXzPXybiEE0+XIkbuj9n5fMeu52gGD/pvqw/Ps6Tm/twwHYW7zNHBWFSVSOMC06BqFUbVgnDp2X5xFL8nJtMrz4tgd/SvyVgGP3u+Crk4hl0jwYs7YWFM6ebVhjj6fcy3zYHMzacjbzv0P8vNQgTad3lka05FMz8II09dv1wVNxC4eJWIA9crMecNRH7nU1QKJMehrsETz9V3g3HDcg6j3L69skeSkl4R/6egXbvY8qIgTD+x+GfowIoIRHHjemHtzI5j+NajJBuSJCTvKqvLoykaZwAC+drKNuqdjBEPrzKRqgjEYLa4oPigOmIYxWdc2BFUJQRbze95GhxG+QBwaSt2GHkWWmWQQgcFC4LycKJAXLoOgseIqHmASTU5murp5T2V8BjbwSNeGzG90kQOxUNjIiP4BDsU4b78LtvdkbbJDx8AZ5oKPsUunUIYmZ8zLNByWM6xdrB3Ith+A8T"
  },
  "api.ebay.com": {
    "compatability": 967,
    "appid": "#",
    "certid": "#",
    "devid": "#",
    "token": "#wVnY+sEZ2PrA2dj6wHkoahAJaBqQudj6x9nY+seQ**0icDAA**AAMAAA**396dRmMG91ia1sJRg4j+bmG6jjSM7CTymxH3pj43BkRBarw8yxUKdgH9FdYC64Kf5oSH2pAiaOP3W+npn641h+duoK72chwNcTIAnjr9EgiSb5HRjXvDZLFuQCFC7MePiOpTlgaXbpWfqV+djgVcC8QE6P3MMj1Sd2c6rKBmHrdx46G4bkh80cSQrBjRhJ6LzTQp2ls1LhgFXbZ7O9B6yWhkyCIP1WtrGGB0f+xwL/a/XQb2Dm4NlGLlAC7VliQC/6YSXT9cY5h4wPJQp7KxLnv9pQozT+4UxeYYbJHF8J2YWXzPXybiEE0+XIkbuj9n5fMeu52gGD/pvqw/Ps6Tm/twwHYW7zNHBWFSVSOMC06BqFUbVgnDp2X5xFL8nJtMrz4tgd/SvyVgGP3u+Crk4hl0jwYs7YWFM6ebVhjj6fcy3zYHMzacjbzv0P8vNQgTad3lka05FMz8II09dv1wVNxC4eJWIA9crMecNRH7nU1QKJMehrsETz9V3g3HDcg6j3L69skeSkl4R/6egXbvY8qIgTD+x+GfowIoIRHHjemHtzI5j+NajJBuSJCTvKqvLoykaZwAC+drKNuqdjBEPrzKRqgjEYLa4oPigOmIYxWdc2BFUJQRbze95GhxG+QBwaSt2GHkWWmWQQgcFC4LycKJAXLoOgseIqHmASTU5murp5T2V8BjbwSNeGzG90kQOxUNjIiP4BDsU4b78LtvdkbbJDx8AZ5oKPsUunUIYmZ8zLNByWM6xdrB3Ith+A8T"
  },
  "svcs.ebay.com": {
    "appid": "#",
    "version": "1.0.0"
  },
  "open.api.ebay.com": {
    "appid": "#",
    "version": 671
  }
}
