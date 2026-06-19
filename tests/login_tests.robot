*** Settings ***
Resource    ../resources/common_keywords.resource
Resource    ../pom_pages/login_page/login_page.resource
Test Setup    Open Login Page
Test Teardown    Close Browser Session

*** Test Cases ***
AUT-WT-LOGIN01: Verify login page loads with all required controls
    [Tags]    WT-LOGIN01    positive
    Verify Login Page Loaded
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN03: Verify successful login using valid credentials via SIGN IN button
    [Tags]    WT-LOGIN03    positive
    Login With Valid Credentials
    Location Should Contain    /washtabui/home

AUT-WT-LOGIN04: Verify successful login using Enter key from password field
    [Tags]    WT-LOGIN04    positive
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Press Keys    ${PASSWORD_FIELD}    ENTER
    Location Should Contain    /washtabui/home

AUT-WT-LOGIN05: Verify login fails with incorrect password
    [Tags]    WT-LOGIN05    negative
    Attempt Login With Credentials    ${VALID_USERNAME}    ${INVALID_PASSWORD}
    Verify Login Failed
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN06: Verify login fails with incorrect username
    [Tags]    WT-LOGIN06    negative
    Attempt Login With Credentials    ${INVALID_USERNAME}    ${VALID_PASSWORD}
    Verify Login Failed
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN07: Verify login fails when both username and password are blank
    [Tags]    WT-LOGIN07    negative
    Attempt Login With Credentials    ${EMPTY}    ${EMPTY}
    Verify Login Failed
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN08: Verify login fails when username is blank
    [Tags]    WT-LOGIN08    negative
    Attempt Login With Credentials    ${EMPTY}    ${VALID_PASSWORD}
    Verify Login Failed
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN09: Verify login fails when password is blank
    [Tags]    WT-LOGIN09    negative
    Attempt Login With Credentials    ${VALID_USERNAME}    ${EMPTY}
    Verify Login Failed
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN10: Verify Home control navigates to home page
    [Tags]    WT-LOGIN10    positive
    Click Home Navigation
    Location Should Contain    /washtabui/home

AUT-WT-LOGIN11: Verify Arrow Back control navigates to home page
    [Tags]    WT-LOGIN11    positive
    Click Back Navigation
    Location Should Contain    /washtabui/home

AUT-WT-LOGIN12: Verify password field masks entered characters
    [Tags]    WT-LOGIN12    positive
    Enter Password    ${VALID_PASSWORD}
    Element Attribute Value Should Be    ${PASSWORD_FIELD}    type    password

AUT-WT-LOGIN13: Verify login fails when username contains only whitespace
    [Tags]    WT-LOGIN13    negative
    Attempt Login With Credentials    ${SPACE}${SPACE}${SPACE}    ${VALID_PASSWORD}
    Verify Login Failed
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN14: Verify login fails when password contains only whitespace
    [Tags]    WT-LOGIN14    negative
    Attempt Login With Credentials    ${VALID_USERNAME}    ${SPACE}${SPACE}${SPACE}
    Verify Login Failed
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN15: Verify login trims leading and trailing spaces in username
    [Tags]    WT-LOGIN15    edge
    Attempt Login With Credentials    ${SPACE}${VALID_USERNAME}${SPACE}    ${VALID_PASSWORD}
    Location Should Contain    /washtabui/home

AUT-WT-LOGIN16: Verify login with extremely long username input
    [Tags]    WT-LOGIN16    edge
    ${LONG_USERNAME}=    Evaluate    "a"*300
    Attempt Login With Credentials    ${LONG_USERNAME}    ${VALID_PASSWORD}
    Verify Login Failed
    Location Should Contain    /washtabui/login

AUT-WT-LOGIN17: Verify multiple rapid clicks on SIGN IN button
    [Tags]    WT-LOGIN17    edge
    Enter Username    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Submit Login Form
    Submit Login Form
    Submit Login Form
    Location Should Contain    /washtabui/home

AUT-WT-LOGIN18: Verify login fails with special characters in username
    [Tags]    WT-LOGIN18    negative
    Attempt Login With Credentials    @@@###$$$    ${VALID_PASSWORD}
    Verify Login Failed
    Location Should Contain    /washtabui/login
