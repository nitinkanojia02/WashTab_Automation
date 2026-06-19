*** Settings ***
Resource    ../resources/common_keywords.resource
Resource    ../pom_pages/login_page/login_page.resource
Test Setup    Run Keywords    Open Login Page    AND    Verify Login Page Ready
Test Teardown    Close Browser Session

*** Test Cases ***
AUT-WT-LOGIN01: Verify login page loads and UI elements are visible
    [Tags]    WT-LOGIN01    positive
    Verify Login Form Loaded
    Verify Login Navigation Controls Visible
    Verify Login Page Url
    Verify Password Field Is Masked

AUT-WT-LOGIN02: Successful login using valid credentials with SIGN IN button
    [Tags]    WT-LOGIN02    positive
    Login With Valid Credentials
    Verify Successful Login Redirect

AUT-WT-LOGIN03: Successful login using Enter key from password field
    [Tags]    WT-LOGIN03    positive
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Press Keys    ${PASSWORD_FIELD}    ENTER
    Verify Successful Login Redirect

AUT-WT-LOGIN04: Login fails with incorrect password
    [Tags]    WT-LOGIN04    negative
    Login With Credentials    ${VALID_USERNAME}    ${INVALID_PASSWORD}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN05: Login fails with incorrect username
    [Tags]    WT-LOGIN05    negative
    Login With Credentials    ${INVALID_USERNAME}    ${VALID_PASSWORD}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN06: Login fails when both username and password are blank
    [Tags]    WT-LOGIN06    negative
    Login With Credentials    ${EMPTY}    ${EMPTY}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN07: Login fails when username is blank
    [Tags]    WT-LOGIN07    negative
    Login With Credentials    ${EMPTY}    ${VALID_PASSWORD}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN08: Login fails when password is blank
    [Tags]    WT-LOGIN08    negative
    Login With Credentials    ${VALID_USERNAME}    ${EMPTY}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN09: Password field masks entered characters
    [Tags]    WT-LOGIN09    positive
    Enter Password    ${VALID_PASSWORD}
    Verify Password Field Is Masked

AUT-WT-LOGIN10: Navigation using Home control from login page
    [Tags]    WT-LOGIN10    positive
    Click Home Navigation Button
    Verify Successful Login Redirect

AUT-WT-LOGIN11: Navigation using Arrow Back control from login page
    [Tags]    WT-LOGIN11    positive
    Click Back Navigation Button
    Verify Successful Login Redirect

AUT-WT-LOGIN12: Login with leading and trailing spaces in username
    [Tags]    WT-LOGIN12    edge
    Login With Credentials    ${SPACE}${VALID_USERNAME}${SPACE}    ${VALID_PASSWORD}
    Verify Successful Login Redirect

AUT-WT-LOGIN13: Login attempt with whitespace-only username
    [Tags]    WT-LOGIN13    negative
    Login With Credentials    ${SPACE}${SPACE}    ${VALID_PASSWORD}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN14: Login attempt with whitespace-only password
    [Tags]    WT-LOGIN14    negative
    Login With Credentials    ${VALID_USERNAME}    ${SPACE}${SPACE}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN15: Login attempt with excessively long username input
    [Tags]    WT-LOGIN15    edge
    Login With Credentials    ${LONG_USERNAME_SAMPLE}    ${VALID_PASSWORD}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN16: Login attempt with special characters in username
    [Tags]    WT-LOGIN16    edge
    Login With Credentials    ${SPECIAL_CHAR_USERNAME}    ${VALID_PASSWORD}
    Verify Login Failed And Still On Login Page

AUT-WT-LOGIN17: Repeated clicking of SIGN IN button during login attempt
    [Tags]    WT-LOGIN17    edge
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click When Ready    ${SIGN_IN_BUTTON}
    Click When Ready    ${SIGN_IN_BUTTON}
    Click When Ready    ${SIGN_IN_BUTTON}
    Verify Successful Login Redirect

AUT-WT-LOGIN18: Login attempt with correct username but wrong case password
    [Tags]    WT-LOGIN18    negative
    Login With Credentials    ${VALID_USERNAME}    ${INVALID_PASSWORD_CASE}
    Verify Login Failed And Still On Login Page
