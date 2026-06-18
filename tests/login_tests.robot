*** Settings ***
Resource    ../resources/common_keywords.resource
Resource    ../pom_pages/login_page/login_page.resource
Test Setup    Open Login Page    http://172.21.166.115/washtabui/login?data=undefined
Test Teardown    Close Browser Session

*** Test Cases ***

WT-LOGIN01: Verify login with valid username and password
    [Tags]    WT-LOGIN01    positive
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Wait Until Element Is Not Visible    ${SIGN_IN_BUTTON}    10s

WT-LOGIN02: Verify login failure with incorrect username and valid password
    [Tags]    WT-LOGIN02    negative
    Verify Login Page Loaded
    Enter User Name    ${INVALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Page Loaded

WT-LOGIN03: Verify login failure with valid username and incorrect password
    [Tags]    WT-LOGIN03    negative
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${INVALID_PASSWORD}
    Click Sign In Button
    Verify Login Page Loaded

WT-LOGIN04: Verify login failure when both username and password are incorrect
    [Tags]    WT-LOGIN04    negative
    Verify Login Page Loaded
    Enter User Name    ${INVALID_USERNAME_ALT}
    Enter Password    ${INVALID_PASSWORD_ALT}
    Click Sign In Button
    Verify Login Page Loaded

WT-LOGIN05: Verify validation when username and password fields are blank
    [Tags]    WT-LOGIN05    negative
    Verify Login Page Loaded
    Enter User Name    ${BLANK_USERNAME}
    Enter Password    ${BLANK_PASSWORD}
    Click Sign In Button
    Verify Username Required Validation
    Verify Password Required Validation

WT-LOGIN06: Verify validation when username is blank and password is entered
    [Tags]    WT-LOGIN06    negative
    Verify Login Page Loaded
    Enter User Name    ${BLANK_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Username Required Validation

WT-LOGIN07: Verify validation when password is blank and username is entered
    [Tags]    WT-LOGIN07    negative
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${BLANK_PASSWORD}
    Click Sign In Button
    Verify Password Required Validation

WT-LOGIN08: Verify username field accepts leading and trailing spaces
    [Tags]    WT-LOGIN08    edge
    Verify Login Page Loaded
    Enter User Name    ${USERNAME_WITH_SPACES}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Wait Until Element Is Not Visible    ${SIGN_IN_BUTTON}    10s

WT-LOGIN09: Verify password field with leading and trailing spaces
    [Tags]    WT-LOGIN09    edge
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${PASSWORD_WITH_SPACES}
    Click Sign In Button
    Verify Login Page Loaded

WT-LOGIN10: Verify login attempt using only whitespace characters
    [Tags]    WT-LOGIN10    negative
    Verify Login Page Loaded
    Enter User Name    ${SPACE_USERNAME}
    Enter Password    ${SPACE_PASSWORD}
    Click Sign In Button
    Verify Username Required Validation
    Verify Password Required Validation

WT-LOGIN11: Verify login with very long username input
    [Tags]    WT-LOGIN11    edge
    Verify Login Page Loaded
    Enter User Name    ${LONG_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Page Loaded

WT-LOGIN12: Verify login with very long password input
    [Tags]    WT-LOGIN12    edge
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${LONG_PASSWORD}
    Click Sign In Button
    Verify Login Page Loaded

WT-LOGIN13: Verify login with special characters in username
    [Tags]    WT-LOGIN13    edge
    Verify Login Page Loaded
    Enter User Name    ${SPECIAL_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Page Loaded

WT-LOGIN14: Verify login with special characters in password
    [Tags]    WT-LOGIN14    edge
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${SPECIAL_PASSWORD}
    Click Sign In Button
    Verify Login Page Loaded

WT-LOGIN15: Verify login button is visible on login page
    [Tags]    WT-LOGIN15    positive
    Verify Login Page Loaded

WT-LOGIN16: Verify password field masks entered characters
    [Tags]    WT-LOGIN16    positive
    Verify Login Page Loaded
    Enter Password    ${VALID_PASSWORD}
    Verify Password Field Is Masked

WT-LOGIN17: Verify pressing Enter key submits login form
    [Tags]    WT-LOGIN17    edge
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Submit Login With Enter Key
    Wait Until Element Is Not Visible    ${SIGN_IN_BUTTON}    10s

WT-LOGIN18: Verify multiple rapid clicks on login button
    [Tags]    WT-LOGIN18    edge
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button Multiple Times    5
    Wait Until Element Is Not Visible    ${SIGN_IN_BUTTON}    10s

WT-LOGIN19: Verify copy paste of credentials into fields
    [Tags]    WT-LOGIN19    positive
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Wait Until Element Is Not Visible    ${SIGN_IN_BUTTON}    10s

WT-LOGIN20: Verify case sensitivity of username
    [Tags]    WT-LOGIN20    edge
    Verify Login Page Loaded
    Enter User Name    ${UPPERCASE_USERNAME}
    Enter Password    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Page Loaded

WT-LOGIN21: Verify case sensitivity of password
    [Tags]    WT-LOGIN21    negative
    Verify Login Page Loaded
    Enter User Name    ${VALID_USERNAME}
    Enter Password    ${LOWERCASE_PASSWORD}
    Click Sign In Button
    Verify Login Page Loaded

WT-LOGIN22: Verify login page loads successfully
    [Tags]    WT-LOGIN22    positive
    Verify Login Page Loaded
