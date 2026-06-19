*** Settings ***
Resource    ../resources/common_keywords.resource
Resource    ../pom_pages/login_page/login_page.resource
Test Setup    Open Login Page    http://172.21.166.115/washtabui/login?data=undefined
Test Teardown    Close Browser Session

*** Test Cases ***
AUT-WT-LOGIN01: Verify login page UI elements are visible
    [Tags]    WT-LOGIN01    positive
    Verify Login Page Loaded
    Verify Navigation Buttons Visible

AUT-WT-LOGIN02: Login with valid username and password
    [Tags]    WT-LOGIN02    positive
    Verify Login Page Loaded
    Perform Login    hacklarr    Icstunnel1
    Verify Successful Login Redirect

AUT-WT-LOGIN03: Login with invalid username and valid password
    [Tags]    WT-LOGIN03    negative
    Verify Login Page Loaded
    Perform Login    invaliduser    Icstunnel1
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN04: Login with valid username and invalid password
    [Tags]    WT-LOGIN04    negative
    Verify Login Page Loaded
    Perform Login    hacklarr    wrongpassword
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN05: Attempt login with empty username and password
    [Tags]    WT-LOGIN05    negative
    Verify Login Page Loaded
    Perform Login    ${EMPTY}    ${EMPTY}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN06: Attempt login with valid username and empty password
    [Tags]    WT-LOGIN06    negative
    Verify Login Page Loaded
    Perform Login    hacklarr    ${EMPTY}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN07: Verify password field masks entered characters
    [Tags]    WT-LOGIN07    positive
    Verify Login Page Loaded
    Enter Password    Icstunnel1
    Verify Password Field Is Masked

AUT-WT-LOGIN08: Verify back navigation button redirects to home page
    [Tags]    WT-LOGIN08    positive
    Verify Login Page Loaded
    Click Back Navigation Button
    Verify Successful Login Redirect

AUT-WT-LOGIN09: Verify home navigation button redirects to home page
    [Tags]    WT-LOGIN09    positive
    Verify Login Page Loaded
    Click Home Navigation Button
    Verify Successful Login Redirect

AUT-WT-LOGIN10: Login attempt with leading and trailing whitespace in username
    [Tags]    WT-LOGIN10    edge
    Verify Login Page Loaded
    Perform Login    ${SPACE}${SPACE}hacklarr${SPACE}${SPACE}    Icstunnel1
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN11: Login with very long username value
    [Tags]    WT-LOGIN11    edge
    Verify Login Page Loaded
    Perform Login    verylongusernamevalueexceedingtypicallengthlimitfortestingpurposes1234567890    Icstunnel1
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN12: Login with special characters in username
    [Tags]    WT-LOGIN12    edge
    Verify Login Page Loaded
    Perform Login    user!@#    Icstunnel1
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN13: Rapid multiple clicks on SIGN IN button with valid credentials
    [Tags]    WT-LOGIN13    edge
    Verify Login Page Loaded
    Enter Username    hacklarr
    Enter Password    Icstunnel1
    Click Sign In Button
    Click Sign In Button
    Click Sign In Button
    Verify Successful Login Redirect
