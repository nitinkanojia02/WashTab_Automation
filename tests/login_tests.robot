*** Settings ***
Resource    ../resources/common_keywords.resource
Resource    ../pom_pages/login_page/login_page.resource
Suite Teardown    Close Browser Session

*** Test Cases ***
AUT-WT-LOGIN01: Verify login page loads and all required UI elements are visible
    [Tags]    WT-LOGIN01    positive
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded

AUT-WT-LOGIN02: Verify successful login using valid credentials via SIGN IN button
    [Tags]    WT-LOGIN02    positive
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Successful Login Redirect

AUT-WT-LOGIN03: Verify login submission using keyboard Enter key after entering valid credentials
    [Tags]    WT-LOGIN03    edge
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Submit Login With Enter Key
    Verify Successful Login Redirect

AUT-WT-LOGIN04: Verify login fails with valid username and incorrect password
    [Tags]    WT-LOGIN04    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${INVALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN05: Verify login fails with invalid username and valid password
    [Tags]    WT-LOGIN05    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${INVALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN06: Verify login fails when both username and password are invalid
    [Tags]    WT-LOGIN06    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${INVALID_USERNAME}
    Enter Password    ${INVALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN07: Verify login attempt when username is empty and password is provided
    [Tags]    WT-LOGIN07    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${EMPTY}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Username Required Validation

AUT-WT-LOGIN08: Verify login attempt when password is empty and username is provided
    [Tags]    WT-LOGIN08    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${EMPTY}
    Click Sign In Button
    Verify Password Required Validation

AUT-WT-LOGIN09: Verify login attempt when both username and password fields are empty
    [Tags]    WT-LOGIN09    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${EMPTY}
    Enter Password    ${EMPTY}
    Click Sign In Button
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN10: Verify password textbox masks entered characters
    [Tags]    WT-LOGIN10    positive
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Password    ${VALID_PASSWORD}
    Verify Password Field Is Masked

AUT-WT-LOGIN11: Verify navigation to home page using home navigation button from login page
    [Tags]    WT-LOGIN11    positive
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Click Home Navigation Button
    Verify Home Navigation Redirects To Home Page

AUT-WT-LOGIN12: Verify navigation to home page using back navigation button from login page
    [Tags]    WT-LOGIN12    positive
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Click Back Navigation Button
    Verify Back Navigation Redirects To Home Page

AUT-WT-LOGIN13: Verify login behavior when credentials contain leading and trailing whitespace
    [Tags]    WT-LOGIN13    edge
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${SPACE}${VALID_USERNAME}${SPACE}
    Enter Password    ${SPACE}${VALID_PASSWORD}${SPACE}
    Click Sign In Button
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN14: Verify login fails when username contains only whitespace characters
    [Tags]    WT-LOGIN14    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${SPACE}${SPACE}${SPACE}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN15: Verify login fails when password contains only whitespace characters
    [Tags]    WT-LOGIN15    negative
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${SPACE}${SPACE}${SPACE}
    Click Sign In Button
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN16: Verify system behavior when SIGN IN button is clicked repeatedly with valid credentials
    [Tags]    WT-LOGIN16    edge
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Click Sign In Button
    Click Sign In Button
    Verify Successful Login Redirect

AUT-WT-LOGIN17: Verify login using credentials pasted into username and password fields
    [Tags]    WT-LOGIN17    edge
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Input Text When Ready    ${USERNAME_TEXTBOX}    ${VALID_USERNAME}
    Input Text When Ready    ${PASSWORD_TEXTBOX}    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Successful Login Redirect

AUT-WT-LOGIN18: Verify login fails when extremely long text values are entered in username and password fields
    [Tags]    WT-LOGIN18    edge
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    ${VALID_USERNAME}${VALID_USERNAME}${VALID_USERNAME}${VALID_USERNAME}${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}${VALID_PASSWORD}${VALID_PASSWORD}${VALID_PASSWORD}${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN19: Verify login behavior when credentials are entered with different letter casing
    [Tags]    WT-LOGIN19    edge
    Open Login Page    ${LOGIN_PAGE_URL}
    Verify Login Page Loaded
    Enter Username    HACKLARR
    Enter Password    ICSTUNNEL1
    Click Sign In Button
    Verify Login Failed And Still On Login Page
